import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useQuery } from "@apollo/client/react";
import { DatasetTable } from "../holdings-table";

vi.mock("@apollo/client/react", () => ({ useQuery: vi.fn() }));
vi.mock("@tanstack/react-router", () => ({ useNavigate: () => vi.fn() }));
vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

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

/** Holdings reports a refused CSV download and keeps the table (w4/329). */
describe("DatasetTable export failure", () => {
  it("says the download failed, then downloads the same rows on retry", async () => {
    const user = userEvent.setup();
    vi.mocked(useQuery).mockReturnValue({
      data: {
        queryShell: {
          resultType: "table",
          table: {
            types: [{ name: "currency" }, { name: "units" }],
            rows: [["ETH", "7.07495"]],
          },
          text: null,
        },
      },
      loading: false,
      error: undefined,
    } as never);
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    URL.revokeObjectURL = vi.fn();
    URL.createObjectURL = vi.fn(() => {
      throw new Error("qa-controlled-holdings-download");
    });
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <DatasetTable
        query="SELECT 1"
        ledgerId="dGVzdE93bmVyfHRlc3RMZWRnZXI="
        ariaLabel="Holdings"
      />,
    );

    const button = screen.getByRole("button", { name: /Export CSV|exportCsv/ });
    button.focus();
    await user.keyboard(" ");
    expect(toast.error).toHaveBeenCalledTimes(1);
    expect(click).not.toHaveBeenCalled();
    expect(screen.getByRole("table", { name: "Holdings" })).toBeInTheDocument();
    expect(button).toHaveFocus();

    let blob: Blob | undefined;
    URL.createObjectURL = vi.fn((made: Blob) => {
      blob = made;
      return "blob:qa";
    });
    await user.keyboard(" ");
    expect(click).toHaveBeenCalledTimes(1);
    expect(await readBlob(blob!)).toContain("7.07495");
  });
});
