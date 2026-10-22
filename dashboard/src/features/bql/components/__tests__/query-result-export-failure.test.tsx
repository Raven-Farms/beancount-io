import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { QueryResultTable } from "@/graphql/definitions";
import { QueryResultExport } from "../query-result-export";

vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ t: (key: string) => key }),
}));

const result = {
  types: [{ name: "qa_label", dtype: "str" }],
  rows: [["qa café 東京"]],
} as unknown as QueryResultTable;

/** jsdom's Blob has no text(); FileReader reads it. */
const readBlob = (blob: Blob) =>
  new Promise<string>((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.readAsText(blob);
  });

const originalCreate = URL.createObjectURL;
const originalRevoke = URL.revokeObjectURL;
afterEach(() => {
  URL.createObjectURL = originalCreate;
  URL.revokeObjectURL = originalRevoke;
  vi.restoreAllMocks();
});

/** A refused download is reported where the reader asked for it (w4/329). */
describe("QueryResultExport download failure", () => {
  it("says the download failed, keeps the button, then downloads on retry", async () => {
    const user = userEvent.setup();
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    URL.revokeObjectURL = vi.fn();
    URL.createObjectURL = vi.fn(() => {
      throw new Error("qa-controlled-download-generation");
    });
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(<QueryResultExport result={result} queryString="SELECT 1" />);

    const button = screen.getByRole("button", { name: /bql.downloadCSV/ });
    button.focus();
    await user.keyboard("{Enter}");
    expect(toast.error).toHaveBeenCalledWith("common.downloadFailed");
    expect(click).not.toHaveBeenCalled();
    expect(button).toHaveFocus();
    expect(button).toBeEnabled();

    // The browser can build it again: the same table downloads.
    let blob: Blob | undefined;
    URL.createObjectURL = vi.fn((made: Blob) => {
      blob = made;
      return "blob:qa";
    });
    await user.keyboard("{Enter}");
    expect(click).toHaveBeenCalledTimes(1);
    expect(toast.error).toHaveBeenCalledTimes(1);
    expect(await readBlob(blob!)).toContain("qa café 東京");
  });
});
