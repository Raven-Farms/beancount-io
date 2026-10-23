import type { QueryResult } from "@rustledger/wasm";
import { collapsedCostOfSumError } from "../cost-of-sum-guard";

/**
 * w23/012. rustledger 0.24.0 answers `cost(sum(position))` over several
 * currencies with one Amount under the first currency's label. The engine's
 * own shapes are stubbed here; `scripts/verify-rustledger.ts` runs the real
 * one.
 */
const amount = (number: string, currency: string) => ({ number, currency });
const inventory = (...units: Array<[string, string]>) => ({
  positions: units.map(([number, currency]) => ({
    units: amount(number, currency),
  })),
});
const result = (columns: string[], rows: unknown[][]): QueryResult =>
  ({ columns, rows, errors: [] }) as unknown as QueryResult;

describe("collapsedCostOfSumError", () => {
  it("leaves a query without cost(sum(position)) alone, running nothing", () => {
    const run = jest.fn();
    expect(
      collapsedCostOfSumError(
        "SELECT sum(position)",
        result(["sum(position)"], []),
        run,
      ),
    ).toBeUndefined();
    expect(run).not.toHaveBeenCalled();
  });

  it("refuses a result whose costs span several currencies", () => {
    const run = jest.fn(() =>
      result(
        ["sum(cost(position))"],
        [[inventory(["-13", "VACHR"], ["4559.74", "USD"])]],
      ),
    );
    const refused = collapsedCostOfSumError(
      "SELECT Cost( SUM(position) ) WHERE account ~ 'Hours|Broker'",
      result(["cost(sum(position))"], [[amount("4546.74", "VACHR")]]),
      run,
    );
    expect(run).toHaveBeenCalledWith(
      "SELECT sum(cost(position)) WHERE account ~ 'Hours|Broker'",
    );
    expect(refused?.rows).toEqual([]);
    expect(refused?.errors).toEqual([
      expect.objectContaining({
        severity: "error",
        message: expect.stringContaining("sum(cost(position))"),
      }),
    ]);
  });

  it("keeps a correct single-currency result, per row", () => {
    expect(
      collapsedCostOfSumError(
        "SELECT account, cost(sum(position)) GROUP BY account",
        result(
          ["account", "cost(sum(position))"],
          [
            ["Assets:Hours", amount("-13", "VACHR")],
            ["Assets:Broker", amount("4559.74", "USD")],
          ],
        ),
        () =>
          result(
            ["account", "sum(cost(position))"],
            [
              ["Assets:Hours", inventory(["-13", "VACHR"])],
              ["Assets:Broker", inventory(["4559.74", "USD"])],
            ],
          ),
      ),
    ).toBeUndefined();
  });

  it("recognizes an aliased column by its shape", () => {
    expect(
      collapsedCostOfSumError(
        "SELECT cost(sum(position)) AS total",
        result(["total"], [[amount("4546.74", "VACHR")]]),
        () => result(["total"], [[inventory(["-13", "VACHR"], ["1", "USD"])]]),
      ),
    ).toBeDefined();
  });

  it("does not judge a column that was already an inventory", () => {
    // `sum(position)` beside it spans currencies in both runs; only the
    // replaced column counts.
    expect(
      collapsedCostOfSumError(
        "SELECT sum(position), cost(sum(position))",
        result(
          ["sum(position)", "cost(sum(position))"],
          [[inventory(["-13", "VACHR"], ["17", "GLD"]), amount("1", "USD")]],
        ),
        () =>
          result(
            ["sum(position)", "sum(cost(position))"],
            [
              [
                inventory(["-13", "VACHR"], ["17", "GLD"]),
                inventory(["1", "USD"]),
              ],
            ],
          ),
      ),
    ).toBeUndefined();
  });

  it("leaves the query's own error to be reported, running nothing", () => {
    const run = jest.fn();
    const failed = {
      columns: [],
      rows: [],
      errors: [{ message: "syntax error", severity: "error" }],
    } as unknown as QueryResult;
    expect(
      collapsedCostOfSumError("SELECT cost(sum(position)) FROM", failed, run),
    ).toBeUndefined();
    expect(run).not.toHaveBeenCalled();
  });
});
