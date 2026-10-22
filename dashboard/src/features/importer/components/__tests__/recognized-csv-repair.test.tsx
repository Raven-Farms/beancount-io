import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ImportWorkflowContainer } from "../import-workflow-container";

// The real CSV parser, upload step and Preview run; only the server's AI
// parser is stubbed, so a test that never sees it called spent no AI tokens.
const parseLLMFile = vi.fn();
vi.mock("../../hooks/use-llm-parser", () => ({
  useLLMParser: () => ({ parseFile: parseLLMFile }),
}));
vi.mock("../../hooks/use-import-submit", () => ({
  useImportSubmit: () => ({
    submitImport: vi.fn(),
    importResult: null,
    isSubmitting: false,
  }),
}));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options?.field
        ? `${String(options.field)} ${String(options.row)}`
        : options
          ? `${key}(${Object.values(options).join(",")})`
          : key,
    i18n: { language: "en" },
  }),
}));
vi.mock("@/common/analytics", () => ({ track: vi.fn() }));
vi.mock("@/common/hooks/use-user-limits", () => ({
  useUserLimits: () => ({ tier: "FREE" }),
}));
vi.mock("@tanstack/react-router", async () => {
  const { routerMock } = await import("@/test/mocks/router");
  return { ...routerMock, useNavigate: () => vi.fn() };
});

function upload(name: string, content: string) {
  const input = document.querySelector<HTMLInputElement>("input[type=file]");
  if (!input) throw new Error("file input missing");
  fireEvent.change(input, {
    target: { files: [new File([content], name, { type: "text/csv" })] },
  });
}

const renderImporter = () =>
  render(
    <ImportWorkflowContainer
      ledgerId="alice/books"
      ledgerOwner="alice"
      ledgerName="books"
    />,
  );

const HEADER = "Date,Payee,Description,Amount";
const continueButton = () =>
  screen.getByRole("button", { name: /^importer\.preview\.continue/ });
const expectNoAiOffer = () => {
  expect(
    screen.queryByRole("button", { name: "importer.aiOffer.parseWithAi" }),
  ).toBeNull();
  expect(parseLLMFile).not.toHaveBeenCalled();
};

beforeEach(() => parseLLMFile.mockReset());

/** A CSV whose columns were read stays local, even with no valid row (w4/961). */
describe("Smart Import keeps a recognized CSV for repair", () => {
  it("previews a sole invalid date for repair, and the corrected date is admitted", async () => {
    const user = userEvent.setup();
    renderImporter();
    upload(
      "invalid-date.csv",
      `${HEADER}\n2026-02-31,qa invalid date,row repair,-12.50\n`,
    );

    const date = await screen.findByRole("button", {
      name: /^importer\.preview\.date \d+$/,
    });
    expect(date).toHaveTextContent("2026-02-31");
    expect(continueButton()).toBeDisabled();
    expectNoAiOffer();

    await user.click(date);
    await user.keyboard("{Control>}a{/Control}2026-02-28{Enter}");
    await waitFor(() => expect(continueButton()).toBeEnabled());
    expect(
      screen.getByRole("button", { name: /^importer\.preview\.date \d+$/ }),
    ).not.toHaveTextContent("2026-02-31");
    expectNoAiOffer();
  });

  it("keeps mixed decimal conventions in Preview with their diagnostics", async () => {
    renderImporter();
    upload(
      "mixed.csv",
      `${HEADER}\n2026-09-01,US,Point,"1,234.56"\n2026-09-02,EU,Comma,"1.234,56"\n`,
    );

    const amounts = await screen.findAllByRole("button", {
      name: /^importer\.preview\.amount \d+$/,
    });
    expect(amounts.map((cell) => cell.textContent)).toEqual([
      expect.stringContaining("1,234.56"),
      expect.stringContaining("1.234,56"),
    ]);
    expect(continueButton()).toBeDisabled();
    expectNoAiOffer();
  });

  it("says a header-only file has no transactions, then previews a replacement", async () => {
    const user = userEvent.setup();
    renderImporter();
    upload("header-only.csv", `${HEADER}\n`);

    expect(
      await screen.findByText("importer.preview.emptyFileTitle"),
    ).toBeInTheDocument();
    expect(continueButton()).toBeDisabled();
    expectNoAiOffer();

    await user.click(
      screen.getByRole("button", { name: "importer.preview.retryUpload" }),
    );
    upload(
      "valid.csv",
      `${HEADER}\n2026-10-21,Cafe,Coffee,-4.50\n2026-10-22,Shop,Bread,-2.00\n`,
    );
    await waitFor(() => expect(continueButton()).toBeEnabled());
    expect(
      screen.getAllByRole("button", { name: /^importer\.preview\.date \d+$/ }),
    ).toHaveLength(2);
    expectNoAiOffer();
  });

  it.each([
    [
      "mixed validity",
      `${HEADER}\n2026-02-31,a,b,-1.00\n2026-10-22,c,d,-1.00\n`,
    ],
    ["unsupported precision", `${HEADER}\n2026-10-22,a,b,9007199254740993\n`],
  ])("still previews %s locally", async (_, csv) => {
    renderImporter();
    upload("control.csv", csv);
    expect(
      await screen.findAllByRole("button", {
        name: /^importer\.preview\.date \d+$/,
      }),
    ).not.toHaveLength(0);
    expectNoAiOffer();
  });

  it.each([
    [
      "unknown columns",
      "Booking date|Counterparty|Value\n03.09.2026|Cafe|-4,50\n",
    ],
    ["records narrower than the header", `${HEADER}\n2026-10-22,Cafe,-4.50\n`],
    ["a headerless file with no valid row", "31.02.2026,Cafe,Coffee,-4.50\n"],
  ])("keeps the AI choice for %s", async (_, csv) => {
    renderImporter();
    upload("unreadable.csv", csv);
    expect(
      await screen.findByRole("button", {
        name: "importer.aiOffer.parseWithAi",
      }),
    ).toBeInTheDocument();
    expect(parseLLMFile).not.toHaveBeenCalled();
    expect(screen.queryByText("importer.preview.emptyFileTitle")).toBeNull();
  });
});
