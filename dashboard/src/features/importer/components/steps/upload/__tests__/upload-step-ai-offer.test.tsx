import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { UploadStep } from "../index";

// The real CSV parser runs; only the server's AI parser is stubbed, so a test
// that never sees it called proves no AI tokens were spent (w3/643).
const parseLLMFile = vi.fn();

vi.mock("../../../../hooks/use-llm-parser", () => ({
  useLLMParser: () => ({ parseFile: parseLLMFile }),
}));

vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ t: (key: string) => key }),
}));

vi.mock("@/common/analytics", () => ({ track: vi.fn() }));

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}));

function upload(container: HTMLElement, name: string, content: string) {
  const input = container.querySelector<HTMLInputElement>("input[type=file]");
  if (!input) throw new Error("file input missing");
  fireEvent.change(input, {
    target: { files: [new File([content], name, { type: "text/csv" })] },
  });
}

const EU_EXPORT = [
  "Date;Payee;Description;Amount",
  "2026-09-03;Cafe;Comma decimal;-4,50",
  "2026-09-04;Shop;Thousand;-1.000",
].join("\n");

const UNREADABLE = "Booking date|Counterparty|Value\n03.09.2026|Cafe|-4,50\n";

const QUOTA_ERROR = {
  errors: [
    {
      message:
        "AI CFO Token limit reached. Maximum: 20000, Current: 21723. Upgrade to Premium or a higher plan to continue.",
      extensions: { code: "RESOURCE_LIMIT_REACHED" },
    },
  ],
};

describe("UploadStep CSV parsing and the AI choice", () => {
  beforeEach(() => {
    parseLLMFile.mockReset();
  });

  it("previews a semicolon EU export without AI parsing", async () => {
    const onParseComplete = vi.fn();
    const { container } = render(
      <UploadStep onParseComplete={onParseComplete} />,
    );

    upload(container, "eu.csv", EU_EXPORT);

    await waitFor(() => expect(onParseComplete).toHaveBeenCalledTimes(1));
    const result = onParseComplete.mock.calls[0][0];
    expect(result.validCount).toBe(2);
    expect(result.rows.map((row: { amount: number }) => row.amount)).toEqual([
      -4.5, -1000,
    ]);
    expect(parseLLMFile).not.toHaveBeenCalled();
  });

  it("asks before parsing an unreadable CSV with AI", async () => {
    const onParseComplete = vi.fn();
    parseLLMFile.mockResolvedValue({
      rows: [],
      validCount: 0,
      errorCount: 0,
      hasErrors: false,
    });
    const { container } = render(
      <UploadStep onParseComplete={onParseComplete} />,
    );

    upload(container, "bank.csv", UNREADABLE);

    const choice = await screen.findByRole("button", {
      name: "importer.aiOffer.parseWithAi",
    });
    expect(screen.getByText("importer.aiOffer.title")).toBeInTheDocument();
    expect(screen.getByText("bank.csv")).toBeInTheDocument();
    expect(parseLLMFile).not.toHaveBeenCalled();
    expect(onParseComplete).not.toHaveBeenCalled();

    fireEvent.click(choice);

    await waitFor(() => expect(onParseComplete).toHaveBeenCalledTimes(1));
    expect(parseLLMFile).toHaveBeenCalledTimes(1);
    expect(parseLLMFile.mock.calls[0][1]).toBe("csv");
  });

  it("goes back to the file picker without AI parsing", async () => {
    const { container } = render(<UploadStep onParseComplete={vi.fn()} />);

    upload(container, "bank.csv", UNREADABLE);
    fireEvent.click(
      await screen.findByRole("button", {
        name: "importer.error.uploadDifferentFile",
      }),
    );

    expect(container.querySelector("input[type=file]")).toBeInTheDocument();
    expect(parseLLMFile).not.toHaveBeenCalled();
  });

  it("names the spent AI tokens, not a file type, when a chosen CSV hits the quota", async () => {
    parseLLMFile.mockRejectedValue(QUOTA_ERROR);
    vi.spyOn(console, "error").mockImplementation(() => {});
    const { container } = render(<UploadStep onParseComplete={vi.fn()} />);

    upload(container, "bank.csv", UNREADABLE);
    fireEvent.click(
      await screen.findByRole("button", {
        name: "importer.aiOffer.parseWithAi",
      }),
    );

    expect(
      await screen.findByText("importer.error.aiQuotaReached"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("importer.error.aiQuotaReachedCsv"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("importer.error.premiumRequiredDescription"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("importer.error.useCsvFormat"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("importer.error.downloadCsvExample"),
    ).toBeInTheDocument();
  });
});
