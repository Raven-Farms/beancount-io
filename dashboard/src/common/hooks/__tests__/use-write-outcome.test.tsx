import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";
import { useWriteOutcome } from "../use-write-outcome";

const state = vi.hoisted(() => ({
  before: [] as { message: string; lineno?: number }[],
  after: [] as { message: string; lineno?: number }[],
  navigate: vi.fn(),
}));

vi.mock("@apollo/client/react", () => ({
  useQuery: () => ({
    data: { getLedgerErrors: state.before },
    refetch: async () => ({ data: { getLedgerErrors: state.after } }),
  }),
}));
vi.mock("@tanstack/react-router", () => ({
  useRouter: () => ({ navigate: state.navigate }),
}));
vi.mock("sonner", () => ({ toast: { warning: vi.fn(), success: vi.fn() } }));

const DUPLICATE_OPEN =
  "Account Assets:Cash is already open (opened on 2026-01-01)";

async function writeAndReport() {
  const { result } = renderHook(() => useWriteOutcome("alice/books"));
  const before = result.current.snapshot();
  let leftErrors = false;
  await act(async () => {
    leftErrors = await result.current.report(before);
  });
  return leftErrors;
}

describe("useWriteOutcome (w3/640)", () => {
  beforeEach(() => {
    vi.mocked(toast.warning).mockClear();
    state.navigate.mockClear();
  });

  it("warns with the first error the write introduced and links to Errors", async () => {
    state.before = [];
    state.after = [{ message: DUPLICATE_OPEN, lineno: 92 }];

    expect(await writeAndReport()).toBe(true);
    expect(toast.warning).toHaveBeenCalledTimes(1);
    const [message, options] = vi.mocked(toast.warning).mock.calls[0]!;
    expect(message).toContain(DUPLICATE_OPEN);
    (options as { action: { onClick: () => void } }).action.onClick();
    expect(state.navigate).toHaveBeenCalledWith({
      to: "/ledger/$ledgerOwner/$ledgerName/errors",
      params: { ledgerOwner: "alice", ledgerName: "books" },
    });
  });

  it("stays quiet when the write added nothing, even if lines moved", async () => {
    state.before = [{ message: "Old problem", lineno: 10 }];
    state.after = [{ message: "Old problem", lineno: 14 }];

    expect(await writeAndReport()).toBe(false);
    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("counts a second copy of an existing error as new", async () => {
    state.before = [{ message: "Same text" }];
    state.after = [{ message: "Same text" }, { message: "Same text" }];

    expect(await writeAndReport()).toBe(true);
  });

  it("does not guess when the errors before the write were unknown", async () => {
    const { result } = renderHook(() => useWriteOutcome("alice/books"));
    state.after = [{ message: DUPLICATE_OPEN }];
    let leftErrors = true;
    await act(async () => {
      leftErrors = await result.current.report(null);
    });
    expect(leftErrors).toBe(false);
    expect(toast.warning).not.toHaveBeenCalled();
  });
});
