import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DeleteBudgetDialog } from "../delete-budget-dialog";
import type { BudgetGroup } from "../types";

const { query, mutate, clearCache } = vi.hoisted(() => ({
  query: vi.fn(),
  mutate: vi.fn(),
  clearCache: vi.fn(),
}));
vi.mock("@apollo/client/react", () => ({
  useApolloClient: () => ({ query }),
  useMutation: () => [mutate],
}));
vi.mock("@/common/hooks/use-apollo-cache", () => ({
  useApolloCacheClear: () => clearCache,
}));
vi.mock("@/common/lib/errors/error-message", () => ({
  useErrorMessage: () => (err: Error) => `formatted: ${err.message}`,
}));

/** A failed Budget delete says so and keeps a retry (w4/233). */
const target = {
  account: "Expenses:Qa",
  interval: "Monthly",
  currency: "USD",
  amount: "123.45 USD",
  entry_hash: "h1",
  date: "2026-10-20",
  budgetHistory: [],
} as unknown as BudgetGroup;
const context = { data: { getLedgerEntryContext: { sha256sum: "abc" } } };

function setup() {
  const onOpenChange = vi.fn();
  const onSuccess = vi.fn();
  render(
    <DeleteBudgetDialog
      target={target}
      ledgerId="qa/books"
      onOpenChange={onOpenChange}
      onSuccess={onSuccess}
    />,
  );
  return { onOpenChange, onSuccess, user: userEvent.setup() };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("DeleteBudgetDialog failures", () => {
  it.each([
    [
      "the context read",
      () => query.mockRejectedValueOnce(new Error("Failed to fetch")),
    ],
    [
      "the delete",
      () => {
        query.mockResolvedValueOnce(context);
        mutate.mockRejectedValueOnce(new Error("Failed to fetch"));
      },
    ],
  ])("reports a failed %s and deletes on retry", async (_case, fail) => {
    fail();
    const { onOpenChange, onSuccess, user } = setup();

    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "formatted: Failed to fetch",
    );
    expect(screen.getByRole("button", { name: "Delete" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeEnabled();
    expect(onOpenChange).not.toHaveBeenCalled();
    expect(onSuccess).not.toHaveBeenCalled();
    expect(clearCache).not.toHaveBeenCalled();

    query.mockResolvedValueOnce(context);
    mutate.mockResolvedValueOnce({ data: {} });
    await user.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
    expect(mutate).toHaveBeenLastCalledWith({
      variables: {
        ledgerId: "qa/books",
        input: { entryHash: "h1", sha256sum: "abc" },
      },
    });
    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(clearCache).toHaveBeenCalledTimes(1);
  });

  it("does not delete without a checksum and says so", async () => {
    query.mockResolvedValueOnce({ data: { getLedgerEntryContext: null } });
    const { onSuccess, user } = setup();

    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong. Please try again.",
    );
    expect(mutate).not.toHaveBeenCalled();
    expect(onSuccess).not.toHaveBeenCalled();
  });
});
