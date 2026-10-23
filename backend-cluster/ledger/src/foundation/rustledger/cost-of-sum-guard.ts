import type { QueryResult } from "@rustledger/wasm";

/**
 * `cost(sum(position))` over more than one currency (w23/012).
 *
 * rustledger 0.24.0 returns a bare Amount for it: the cost numbers of every
 * currency summed under the first currency's label (`-13 VACHR` and
 * `17 GLD {268.22 USD}` come back as `4546.74 VACHR`), where beanquery returns
 * one inventory entry per currency. Correct over one currency, so the query is
 * not refused outright: the equivalent `sum(cost(position))`, which the engine
 * does return as an inventory, is run alongside, and only a result it shows to
 * span several currencies is refused, naming the spelling that works. This is
 * a guard, not a BQL rewrite — the user's query is never answered with a
 * different query's rows. Remove it once the engine is fixed upstream; the
 * live check in `scripts/verify-rustledger.ts` shows when.
 */
const COST_OF_SUM = /cost\s*\(\s*sum\s*\(\s*position\s*\)\s*\)/i;
const EQUIVALENT = "sum(cost(position))";

const isInventory = (cell: unknown): cell is { positions: unknown[] } =>
  Array.isArray((cell as { positions?: unknown } | null)?.positions);

function currencyCount(cell: { positions: unknown[] }): number {
  return new Set(
    cell.positions.map(
      (position) =>
        (position as { units?: { currency?: unknown } }).units?.currency,
    ),
  ).size;
}

/**
 * The query error for a collapsed `cost(sum(position))`, or `undefined` when
 * the query does not use it or every row's cost is in one currency.
 *
 * The replaced columns are the ones the probe returns as inventories where the
 * user's query did not — found by shape rather than by name, so an alias
 * (`cost(sum(position)) AS total`) is still recognized.
 */
export function collapsedCostOfSumError(
  query: string,
  result: QueryResult,
  run: (query: string) => QueryResult,
): QueryResult | undefined {
  if (!COST_OF_SUM.test(query)) return undefined;
  if (result.errors.some((error) => error.severity === "error")) {
    return undefined;
  }
  const probe = run(
    query.replace(new RegExp(COST_OF_SUM.source, "gi"), EQUIVALENT),
  );
  if (probe.errors.some((error) => error.severity === "error")) {
    return undefined;
  }
  const replaced = probe.columns
    .map((_, index) => index)
    .filter(
      (index) =>
        probe.rows.some((row) => isInventory(row[index])) &&
        !result.rows.some((row) => isInventory(row[index])),
    );
  const collapsed = probe.rows.some((row) =>
    replaced.some((index) => {
      const cell = row[index];
      return isInventory(cell) && currencyCount(cell) > 1;
    }),
  );
  if (!collapsed) return undefined;
  return {
    columns: [],
    rows: [],
    errors: [
      {
        message:
          "cost(sum(position)) spans more than one currency here, and the query engine would return their costs summed under a single currency. Use sum(cost(position)), which returns one amount per currency.",
        code: null,
        phase: "query",
        hint: "Replace cost(sum(position)) with sum(cost(position)).",
        file: null,
        line: null,
        column: null,
        end_line: null,
        end_column: null,
        severity: "error",
      },
    ],
  };
}
