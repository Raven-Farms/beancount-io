import { act, renderHook, waitFor } from "@testing-library/react";
import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
} from "@apollo/client";
import { ApolloProvider } from "@apollo/client/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { groupBudgetEntries } from "../budget-utils";
import { useBudgetEntries } from "../use-budget-entries";

/**
 * The journal pages its results; the Budget page must read all of them
 * (w4/235). The link below serves real `{ total, data }` page shapes.
 */
function budget(account: string, number: string, date = "2026-10-01") {
  return {
    date,
    entry_hash: `${account}-${date}-${number}`,
    directive_type: "Custom",
    type: "budget",
    values: [account, "monthly", { number, currency: "USD" }],
  };
}

function setup(ledger: unknown[], failOffsets = new Set<number>()) {
  const requests: Array<{ limit: number; offset: number }> = [];
  const link = new ApolloLink((operation) => {
    const { limit = 20, offset = 0 } = operation.variables.query ?? {};
    requests.push({ limit, offset });
    return new Observable((observer) => {
      if (failOffsets.has(offset)) {
        failOffsets.delete(offset);
        observer.error(new Error("Failed to fetch"));
        return;
      }
      observer.next({
        data: {
          getLedgerJournal: {
            __typename: "JournalResponse",
            total: ledger.length,
            data: ledger.slice(offset, offset + limit),
            is_empty: ledger.length === 0,
          },
        },
      });
      observer.complete();
    });
  });
  const client = new ApolloClient({ link, cache: new InMemoryCache() });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <ApolloProvider client={client}>{children}</ApolloProvider>
  );
  return {
    requests,
    hook: renderHook(() => useBudgetEntries("qa/books"), { wrapper }),
  };
}

describe("useBudgetEntries", () => {
  it("loads all 21 accounts of the QA fixture", async () => {
    const ledger = Array.from({ length: 21 }, (_, i) =>
      budget(`Expenses:Budget${String(21 - i).padStart(2, "0")}`, `${21 - i}`),
    );
    const { hook } = setup(ledger);
    await waitFor(() => expect(hook.result.current.entries).not.toBeNull());
    const accounts = groupBudgetEntries(hook.result.current.entries!).map(
      (group) => group.account,
    );
    expect(accounts).toHaveLength(21);
    expect(accounts).toContain("Expenses:Budget01");
  });

  it("reads past the first page, including an older target", async () => {
    // Newest first: 149 single-target accounts, then the older Food target.
    const ledger = [
      budget("Expenses:Food", "300", "2026-09-01"),
      ...Array.from({ length: 148 }, (_, i) => budget(`Expenses:A${i}`, "1")),
      budget("Expenses:Food", "200", "2026-01-01"),
    ];
    const { hook, requests } = setup(ledger);
    expect(hook.result.current.entries).toBeNull();
    await waitFor(() => expect(hook.result.current.entries).toHaveLength(150));
    expect(requests.map((r) => r.offset)).toEqual([0, 100]);
    const food = groupBudgetEntries(
      hook.result.current.entries!,
      "2026-10-20",
    ).find((group) => group.account === "Expenses:Food")!;
    expect(food.budgetHistory.map((entry) => entry.amount)).toEqual([
      "200 USD",
      "300 USD",
    ]);
  });

  it("reports a failed later page instead of a partial history, then retries", async () => {
    const ledger = Array.from({ length: 120 }, (_, i) =>
      budget(`Expenses:A${i}`, "1"),
    );
    const { hook } = setup(ledger, new Set([100]));
    await waitFor(() => expect(hook.result.current.error).toBeDefined());
    expect(hook.result.current.entries).toBeNull();
    expect(hook.result.current.loading).toBe(false);

    act(() => hook.result.current.retry());
    await waitFor(() => expect(hook.result.current.entries).toHaveLength(120));
    expect(hook.result.current.error).toBeUndefined();
  });

  it("keeps an empty ledger empty", async () => {
    const { hook } = setup([]);
    await waitFor(() => expect(hook.result.current.entries).toEqual([]));
    expect(hook.result.current.loading).toBe(false);
  });
});
