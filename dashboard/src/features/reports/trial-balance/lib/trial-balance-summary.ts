import type { HierarchyListNode } from "@/features/reports/balance-sheet/hierarchy-list-types";
import { sumBalanceRecords } from "@/features/reports/export/model";
import { isZeroStatementAmount } from "@/features/reports/export/presentation";

function rootBalance(node: HierarchyListNode): Record<string, unknown> {
  return (node.balanceChildren ?? node.balance ?? {}) as Record<
    string,
    unknown
  >;
}

/**
 * Per-unit sum of the trial-balance roots' signed accounting balances — zero
 * when debits equal credits. The `inverted` flag only changes how credit rows
 * are displayed; summing display signs reported a balanced ledger as out by
 * twice its credits (w4/267).
 */
export function computeTrialBalanceReconciliation(
  hierarchyData: HierarchyListNode[],
): Record<string, string> {
  if (hierarchyData.length === 0) {
    return {};
  }
  return sumBalanceRecords(hierarchyData.map(rootBalance));
}

export function hasTrialBalanceReconciliationDifference(
  difference: Record<string, string>,
): boolean {
  return Object.values(difference).some(
    (value) => !isZeroStatementAmount(value),
  );
}
