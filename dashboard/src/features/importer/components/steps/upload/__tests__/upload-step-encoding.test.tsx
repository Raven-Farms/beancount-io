import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { UploadStep } from "../index";

// Real bytes run through the real reader, decoder and CSV parser; only the
// server's AI parser is stubbed, to prove it is never called (w4/278).
const parseLLMFile = vi.fn();

vi.mock("../../../../hooks/use-llm-parser", () => ({
  useLLMParser: () => ({ parseFile: parseLLMFile }),
}));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ t: (key: string) => key }),
}));
vi.mock("@/common/analytics", () => ({ track: vi.fn() }));
vi.mock("@tanstack/react-router", async () => {
  const { routerMock } = await import("@/test/mocks/router");
  return routerMock;
});
vi.mock("@/common/hooks/use-user-limits", () => ({
  useUserLimits: () => ({ tier: "FREE" }),
}));

const HEADER = "Date,Payee,Description,Amount\r\n";
const ascii = (text: string) => [...text].map((char) => char.charCodeAt(0));

/** The note's 85-byte CP1252 seed: é is E9, è is E8. */
const CP1252 = new Uint8Array([
  ...ascii(HEADER),
  ...ascii("2026-01-01,qa-20261020 Caf"),
  0xe9,
  ...ascii(",qa-20261020 Cr"),
  0xe8,
  ...ascii("me,-12.50\r\n"),
]);
const TEXT = `${HEADER}2026-01-01,qa-20261020 Café,qa-20261020 Crème,-12.50\r\n`;

function utf16(text: string, bigEndian: boolean): Uint8Array {
  const bytes = [bigEndian ? 0xfe : 0xff, bigEndian ? 0xff : 0xfe];
  for (const char of text) {
    const unit = char.charCodeAt(0);
    const pair = [unit & 0xff, unit >> 8];
    bytes.push(...(bigEndian ? pair.reverse() : pair));
  }
  return new Uint8Array(bytes);
}

function upload(container: HTMLElement, bytes: BlobPart) {
  const input = container.querySelector<HTMLInputElement>("input[type=file]");
  if (!input) throw new Error("file input missing");
  fireEvent.change(input, {
    target: {
      files: [
        new File([bytes], "qa-20261020-import.csv", { type: "text/csv" }),
      ],
    },
  });
}

describe("UploadStep source encoding", () => {
  beforeEach(() => {
    parseLLMFile.mockReset();
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("refuses a CP1252 CSV with re-save guidance, no AI, and a new-file path", async () => {
    expect(CP1252).toHaveLength(85);
    const onParseComplete = vi.fn();
    const { container } = render(
      <UploadStep onParseComplete={onParseComplete} />,
    );

    upload(container, CP1252);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("importer.error.notUtf8");
    expect(alert).toHaveTextContent("importer.error.notUtf8Description");
    expect(screen.queryByText("importer.aiOffer.title")).toBeNull();
    expect(onParseComplete).not.toHaveBeenCalled();
    expect(parseLLMFile).not.toHaveBeenCalled();

    fireEvent.click(
      screen.getByRole("button", {
        name: "importer.error.uploadDifferentFile",
      }),
    );
    upload(container, TEXT);
    await waitFor(() => expect(onParseComplete).toHaveBeenCalledTimes(1));
    expect(onParseComplete.mock.calls[0][0].rows[0].payee).toBe(
      "qa-20261020 Café",
    );
  });

  it.each([
    ["UTF-8", new TextEncoder().encode(TEXT)],
    [
      "UTF-8 with a BOM",
      new Uint8Array([0xef, 0xbb, 0xbf, ...new TextEncoder().encode(TEXT)]),
    ],
    ["UTF-16LE with a BOM", utf16(TEXT, false)],
    ["UTF-16BE with a BOM", utf16(TEXT, true)],
  ])("keeps the text of %s", async (_, bytes) => {
    const onParseComplete = vi.fn();
    const { container } = render(
      <UploadStep onParseComplete={onParseComplete} />,
    );

    upload(container, bytes);

    await waitFor(() => expect(onParseComplete).toHaveBeenCalledTimes(1));
    const result = onParseComplete.mock.calls[0][0];
    expect(result.validCount).toBe(1);
    expect(result.rows[0]).toMatchObject({
      payee: "qa-20261020 Café",
      description: "qa-20261020 Crème",
      amount: -12.5,
    });
    expect(parseLLMFile).not.toHaveBeenCalled();
  });

  it("keeps a literal U+FFFD in valid UTF-8", async () => {
    const onParseComplete = vi.fn();
    const { container } = render(
      <UploadStep onParseComplete={onParseComplete} />,
    );

    upload(container, `${HEADER}2026-01-01,qa �,qa,-1.00\r\n`);

    await waitFor(() => expect(onParseComplete).toHaveBeenCalledTimes(1));
    expect(onParseComplete.mock.calls[0][0].rows[0].payee).toBe("qa �");
  });
});
