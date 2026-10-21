import { atValueError } from "../at-value-guard";

/** w23/020: the engine answers `AT value` shorthands in units. */
describe("atValueError", () => {
  it.each([
    ["BALANCES AT value", "value(sum(position))"],
    ["balances at VALUE where account ~ 'Broker'", "value(sum(position))"],
    ["  BALANCES FROM year = 2021 AT value", "value(sum(position))"],
    ["JOURNAL 'Assets:Broker' AT value", "value(balance)"],
  ])("refuses %p, naming %s", (query, supported) => {
    const refused = atValueError(query);
    expect(refused?.rows).toEqual([]);
    expect(refused?.errors[0]).toMatchObject({
      severity: "error",
      message: expect.stringContaining(supported),
    });
  });

  it.each([
    "BALANCES",
    "BALANCES AT cost",
    "JOURNAL 'Assets:Broker' AT units",
    "SELECT account, value(sum(position)) GROUP BY account",
    // The words inside a string literal are not the clause.
    "JOURNAL 'Assets:Sold at value'",
    "SELECT narration WHERE narration = 'balances at value'",
  ])("leaves %p alone", (query) => {
    expect(atValueError(query)).toBeUndefined();
  });
});
