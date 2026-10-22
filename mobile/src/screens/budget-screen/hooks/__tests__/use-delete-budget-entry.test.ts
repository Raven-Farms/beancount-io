import fs from "fs";
import path from "path";
import vm from "vm";
import ts from "typescript";
import { classifyStaleDelete } from "../../../transaction-detail-screen/delete-transaction";

/**
 * w21/393: deleting a budget entry that changed elsewhere ended in a bare
 * "Failed to delete budget", and every retry failed the same way (its hash no
 * longer resolves). Runs the real hook with React and Apollo stubbed.
 */
const notFound = Object.assign(new Error("Ledger resource not found"), {
  graphQLErrors: [{ message: "x", extensions: { code: "NOT_FOUND" } }],
});
const unavailable = Object.assign(new Error("down"), {
  graphQLErrors: [
    { message: "x", extensions: { code: "SERVICE_UNAVAILABLE" } },
  ],
});

function run(error: unknown) {
  const refreshed: string[] = [];
  const exports: Record<string, any> = {};
  const modules: Record<string, unknown> = {
    "@/translations": {
      i18n: { t: (key: string) => key },
    },
    "@/common/ledger-refusal": {
      ledgerWriteFailureMessage: () => null,
    },
    react: {
      useCallback: (fn: unknown) => fn,
      useState: (v: unknown) => [v, () => {}],
    },
    "@apollo/client": {
      useApolloClient: () => ({
        query: async () => {
          throw error;
        },
      }),
    },
    "@/generated-graphql/graphql": {
      GetLedgerEntryContextDocument: {},
      useDeleteLedgerEntrySourceSliceMutation: () => [async () => ({})],
    },
    "@/common/apollo/invalidate-ledger": {
      invalidateLedgerData: async (_client: unknown, scope: string) => {
        refreshed.push(scope);
      },
    },
    "@/common/hooks/use-ledger-access": {
      useLedgerAccess: () => ({ canWrite: true }),
    },
    "@/screens/transaction-detail-screen/delete-transaction": {
      classifyStaleDelete,
    },
    "@/screens/budget-screen/hooks/use-budget-groups": {},
  };
  vm.runInNewContext(
    ts.transpileModule(
      fs.readFileSync(
        path.join(__dirname, "../use-delete-budget-entry.ts"),
        "utf8",
      ),
      { compilerOptions: { module: ts.ModuleKind.CommonJS } },
    ).outputText,
    {
      exports,
      require: (id: string) => {
        if (!(id in modules)) throw new Error(`Unexpected dependency ${id}`);
        return modules[id];
      },
    },
  );
  const { deleteBudgetEntry } = exports.useDeleteBudgetEntry("alice/books");
  return deleteBudgetEntry("hash-1").then((result: unknown) => ({
    result: JSON.parse(JSON.stringify(result)),
    refreshed,
  }));
}

describe("deleting a budget entry that changed elsewhere", () => {
  it("refreshes the history and says the entry changed", async () => {
    const { result, refreshed } = await run(notFound);
    expect(result).toEqual({ ok: false, message: "budgetDeleteChanged" });
    expect(refreshed).toEqual(["entries"]);
  });

  it("treats a conflict the same way", async () => {
    const { result, refreshed } = await run(
      new Error("sha does not match [given: a, expected: b]"),
    );
    expect(result.message).toBe("budgetDeleteChanged");
    expect(refreshed).toEqual(["entries"]);
  });

  it("leaves any other failure to the generic message, with no refresh", async () => {
    const { result, refreshed } = await run(unavailable);
    expect(result).toEqual({ ok: false, message: null });
    expect(refreshed).toEqual([]);
  });
});
