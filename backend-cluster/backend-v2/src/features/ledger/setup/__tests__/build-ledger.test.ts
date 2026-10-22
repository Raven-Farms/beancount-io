import { ValidationError } from "@/shared/errors";
import {
  buildLedgerFiles,
  previewLedgerSetup,
  type LedgerSetup,
} from "../build-ledger";
import fixturesJson from "../fixtures.json";

describe("buildLedgerFiles (w3/m53/t002)", () => {
  it("builds the personal preset with a known opening balance", () => {
    const files = buildLedgerFiles(
      {
        preset: "personal@1",
        title: "Household",
        operatingCurrency: "EUR",
        historyStart: "2026-02-01",
        accounts: [
          {
            name: "Assets:Cash",
            openingState: "known",
            amount: "100",
          },
        ],
      },
      "2026-01-01",
    );
    const main = files["main.bean"];
    expect(main).toContain('option "title" "Household"');
    expect(main).toContain('option "operating_currency" "EUR"');
    // Accounts open the day before the boundary so the opening transaction
    // can post then; the assertion stays on the boundary.
    expect(main).toContain("2026-01-31 open Assets:Cash EUR");
    // Opening transaction lands the day before the history boundary and the
    // assertion on the boundary itself (fixture personal@1-opening-known).
    expect(main).toContain('2026-01-31 * "Opening balance"');
    expect(main).toContain("Assets:Cash 100 EUR");
    expect(main).toContain("Equity:OpeningBalances -100 EUR");
    expect(main).toContain("2026-02-01 balance Assets:Cash 100 EUR");
  });

  it("keeps unknown and zero opening states distinct", () => {
    const unknown = buildLedgerFiles(
      {
        preset: "personal@1",
        operatingCurrency: "EUR",
        historyStart: "2026-02-01",
        accounts: [{ name: "Assets:Cash", openingState: "unknown" }],
      },
      "2026-01-01",
    )["main.bean"];
    expect(unknown).toContain('bcio_opening_balance_status: "unknown"');
    expect(unknown).not.toContain("balance Assets:Cash");

    const zero = buildLedgerFiles(
      {
        preset: "personal@1",
        operatingCurrency: "EUR",
        historyStart: "2026-02-01",
        accounts: [{ name: "Assets:Cash", openingState: "zero" }],
      },
      "2026-01-01",
    )["main.bean"];
    expect(zero).toContain('bcio_opening_balance_status: "zero"');
    expect(zero).not.toContain("balance Assets:Cash");
  });

  it("opens capability accounts only when the capability is enabled", () => {
    const deferred = buildLedgerFiles(
      { preset: "freelance@1", historyStart: "2026-01-01" },
      "2026-01-01",
    )["main.bean"];
    expect(deferred).not.toContain("Assets:AccountsReceivable");

    const enabled = buildLedgerFiles(
      {
        preset: "freelance@1",
        historyStart: "2026-01-01",
        capabilities: { invoices: "enabled" },
      },
      "2026-01-01",
    )["main.bean"];
    expect(enabled).toContain("Assets:AccountsReceivable");
  });

  it("refuses invalid explicit values and creates nothing", () => {
    expect(() =>
      buildLedgerFiles({ preset: "nope@1" as never }, "2026-01-01"),
    ).toThrow(ValidationError);
    expect(() =>
      buildLedgerFiles(
        { preset: "personal@1", operatingCurrency: "ZZZ" },
        "2026-01-01",
      ),
    ).toThrow(ValidationError);
    expect(() =>
      buildLedgerFiles(
        { preset: "personal@1", historyStart: "2026-13-01" },
        "2026-01-01",
      ),
    ).toThrow(ValidationError);
    expect(() =>
      buildLedgerFiles(
        {
          preset: "personal@1",
          accounts: [{ name: "Assets:Cash", openingState: "known" }],
        },
        "2026-01-01",
      ),
    ).toThrow(ValidationError);
    expect(() =>
      buildLedgerFiles(
        {
          preset: "personal@1",
          accounts: [{ name: "Assets:Nope", openingState: "zero" }],
        },
        "2026-01-01",
      ),
    ).toThrow(ValidationError);
  });

  // w21/438: the arguments were swapped, so `field` held the whole sentence and
  // the message read "Validation failed for Unsupported operating currency …: setup".
  it("names the setup as the field and the problem as the reason", () => {
    let thrown: unknown;
    try {
      buildLedgerFiles(
        { preset: "personal@1", operatingCurrency: "XX" },
        "2026-01-01",
      );
    } catch (error) {
      thrown = error;
    }
    expect(thrown).toBeInstanceOf(ValidationError);
    const error = thrown as ValidationError;
    expect(error.metadata).toMatchObject({ field: "setup" });
    expect(String(error.metadata?.reason)).toContain(
      "Unsupported operating currency",
    );
    expect(error.message).toMatch(
      /^Validation failed for setup: .*Unsupported operating currency/,
    );
  });

  it("matches every clean conformance fixture (w3/m53/t005)", () => {
    const clean = fixturesJson.fixtures.filter((fixture) =>
      fixture.id.endsWith("-clean"),
    );
    expect(clean).toHaveLength(8);
    for (const fixture of clean) {
      const preview = previewLedgerSetup(fixture.spec as LedgerSetup, "2026-01-01");
      expect(preview.accounts).toEqual(
        [...(fixture.expected.openedAccounts ?? [])].sort(),
      );
      for (const optional of fixture.expected.optionalAccountsNotOpened ?? []) {
        expect(preview.accounts).not.toContain(optional);
      }
      expect(preview.files["main.bean"]).not.toContain(" balance ");
    }
  });

  it("matches the opening conformance fixtures", () => {
    const known = previewLedgerSetup(
      {
        preset: "personal@1",
        operatingCurrency: "EUR",
        historyStart: "2026-02-01",
        accounts: [
          { name: "Assets:Cash", openingState: "known", amount: "100" },
        ],
      },
      "2026-01-01",
    );
    expect(known.files["main.bean"]).toContain('2026-01-31 * "Opening balance"');
    expect(known.files["main.bean"]).toContain(
      "2026-02-01 balance Assets:Cash 100 EUR",
    );
  });

  // w21/104: a credit card's 500 owed was written as +500, raising net worth.
  it("stores a liability's amount owed as the negative posting", () => {
    const main = previewLedgerSetup(
      {
        preset: "personal@1",
        operatingCurrency: "USD",
        historyStart: "2026-02-01",
        accounts: [
          { name: "Liabilities:CreditCard", openingState: "known", amount: "500" },
          { name: "Assets:Cash", openingState: "known", amount: "100" },
        ],
      },
      "2026-01-01",
    ).files["main.bean"];
    expect(main).toContain("  Liabilities:CreditCard -500 USD");
    expect(main).toContain("  Equity:OpeningBalances 500 USD");
    expect(main).toContain("2026-02-01 balance Liabilities:CreditCard -500 USD");
    // Assets are unchanged.
    expect(main).toContain("2026-02-01 balance Assets:Cash 100 USD");
  });

  it("keeps an explicit negative on a liability as written", () => {
    const main = previewLedgerSetup(
      {
        preset: "personal@1",
        historyStart: "2026-02-01",
        accounts: [
          { name: "Liabilities:CreditCard", openingState: "known", amount: "-30.50" },
        ],
      },
      "2026-01-01",
    ).files["main.bean"];
    expect(main).toContain("2026-02-01 balance Liabilities:CreditCard -30.50 USD");
    expect(main).not.toContain("--30.50");
  });

  // w21/107: Date.parse rolled 2026-04-31 over to 1 May, so it was accepted.
  it("refuses a history start that is not a calendar day", () => {
    for (const historyStart of ["2026-02-30", "2026-04-31", "2025-02-29"]) {
      expect(() =>
        previewLedgerSetup({ preset: "personal@1", historyStart }, "2026-01-01"),
      ).toThrow(`Invalid history start "${historyStart}"`);
    }
    expect(
      previewLedgerSetup(
        { preset: "personal@1", historyStart: "2024-02-29" },
        "2026-01-01",
      ).files["main.bean"],
    ).toContain("2024-02-29 open");
  });

  it("builds a blank ledger with no accounts", () => {
    const main = buildLedgerFiles(
      { preset: "blank@1", title: "Books", operatingCurrency: "JPY" },
      "2026-01-01",
    )["main.bean"];
    expect(main).not.toContain(" open ");
    expect(main).toContain('option "operating_currency" "JPY"');
  });
});
