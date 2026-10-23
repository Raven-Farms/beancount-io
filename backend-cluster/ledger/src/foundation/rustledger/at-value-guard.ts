import type { QueryResult } from "@rustledger/wasm";

/**
 * `BALANCES … AT value` and `JOURNAL … AT value` (w23/020).
 *
 * rustledger 0.24.0 ignores the clause and returns units — `{VHT: 4}` where
 * beanquery returns `{USD: 480.00}` — so a table labelled as market values was
 * a holdings count. Refused before the query runs, naming the `value()` form
 * the engine does evaluate. Not a rewrite: the user's query is never answered
 * with another query's rows. Remove once the engine honours the clause; the
 * live check in `scripts/verify-rustledger.ts` shows when.
 */
const AT_VALUE = /^\s*(balances|journal)\b[\s\S]*\bat\s+value\b/i;

/** The query error for an `AT value` shorthand, or `undefined`. */
export function atValueError(query: string): QueryResult | undefined {
  // String literals may name an account or narration that says "at value".
  const unquoted = query.replace(/'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"/g, "''");
  const statement = AT_VALUE.exec(unquoted)?.[1]?.toUpperCase();
  if (statement === undefined) return undefined;
  const supported =
    statement === "BALANCES"
      ? "SELECT account, value(sum(position)) GROUP BY account"
      : "SELECT date, account, value(position), value(balance) WHERE account ~ '…'";
  return {
    columns: [],
    rows: [],
    errors: [
      {
        message: `${statement} … AT value is not supported by this query engine: it would return units, not market values. Use ${supported} instead.`,
        code: null,
        phase: "query",
        hint: `Replace the AT value shorthand with ${supported}.`,
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
