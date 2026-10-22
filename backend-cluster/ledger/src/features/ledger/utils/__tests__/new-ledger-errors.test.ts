import { newLedgerErrors, refuseNewLedgerErrors } from "../new-ledger-errors";
import { NewLedgerErrorsError } from "@/shared/errors";

const at = (message: string, filename: string, lineno: number) => ({
  message,
  source: { filename, lineno },
});

describe("newLedgerErrors", () => {
  it("returns only the errors the projection adds", () => {
    const before = [at("Balance failed for Assets:Cash", "main.bean", 4)];
    const after = [
      at("Balance failed for Assets:Cash", "main.bean", 4),
      at("Duplicate open directive for Assets:Cash", "main.bean", 12),
    ];
    expect(newLedgerErrors(before, after)).toEqual([
      at("Duplicate open directive for Assets:Cash", "main.bean", 12),
    ]);
  });

  it("treats the same message at another position as new", () => {
    const before = [
      at("Duplicate open directive for Assets:Cash", "main.bean", 3),
    ];
    const after = [
      at("Duplicate open directive for Assets:Cash", "main.bean", 3),
      at("Duplicate open directive for Assets:Cash", "main.bean", 9),
    ];
    expect(newLedgerErrors(before, after)).toEqual([after[1]]);
  });

  // w21/367: interpolation and lot-match errors end with the entry's date and
  // narration, so editing either made the existing error read as a new one.
  describe("an error that quotes the entry's date and narration", () => {
    const interpolation = (date: string, narration: string) =>
      `interpolation failed: cannot infer currency for posting to account Expenses:QaInterp (${date}, "${narration}")`;
    const lot = (date: string, narration: string) =>
      `Ambiguous lot match for 10 AAPL {} (${date}, "${narration}")`;

    it("is not new after a narration-only edit", () => {
      const before = [
        at(interpolation("2026-08-30", "Groceries"), "main.bean", 3),
      ];
      const after = [
        at(interpolation("2026-08-30", "Groceries edited"), "main.bean", 3),
      ];
      expect(newLedgerErrors(before, after)).toEqual([]);
    });

    it("is not new after a date-only edit, nor for a lot match", () => {
      expect(
        newLedgerErrors(
          [at(interpolation("2026-08-30", "Groceries"), "main.bean", 3)],
          [at(interpolation("2026-09-02", "Groceries"), "main.bean", 3)],
        ),
      ).toEqual([]);
      expect(
        newLedgerErrors(
          [at(lot("2026-03-01", "Sell"), "main.bean", 8)],
          [at(lot("2026-03-04", 'Sell "all"'), "main.bean", 8)],
        ),
      ).toEqual([]);
    });

    it("still counts a second broken entry, a different message and another file as new", () => {
      const old = at(interpolation("2026-08-30", "Groceries"), "main.bean", 3);
      const second = at(interpolation("2026-09-01", "Rent"), "main.bean", 9);
      expect(newLedgerErrors([old], [old, second])).toEqual([second]);
      const other = at(
        'interpolation failed: cannot infer currency for posting to account Expenses:Other (2026-08-30, "Groceries")',
        "main.bean",
        3,
      );
      expect(newLedgerErrors([old], [other])).toEqual([other]);
      const elsewhere = at(old.message, "other.bean", 3);
      expect(newLedgerErrors([old], [elsewhere])).toEqual([elsewhere]);
    });
  });

  it("matches errors without a source by message", () => {
    expect(
      newLedgerErrors(
        [{ message: "Plugin failed" }],
        [{ message: "Plugin failed" }],
      ),
    ).toEqual([]);
    expect(newLedgerErrors([], [{ message: "Plugin failed" }])).toEqual([
      { message: "Plugin failed" },
    ]);
  });

  it("finds nothing new for a clean write", () => {
    expect(newLedgerErrors([], [])).toEqual([]);
  });
});

describe("newLedgerErrors after an edit or delete", () => {
  it("does not count an existing error the write moved to another line", () => {
    // Deleting a block above it shifts the duplicate open up (w21/m1).
    const before = [
      at("Duplicate open directive for Assets:Cash", "main.bean", 90),
    ];
    const after = [
      at("Duplicate open directive for Assets:Cash", "main.bean", 87),
    ];
    expect(newLedgerErrors(before, after)).toEqual([]);
  });

  it("keeps the same message in another file apart", () => {
    const before = [
      at("Duplicate open directive for Assets:Cash", "a.bean", 3),
    ];
    const after = [at("Duplicate open directive for Assets:Cash", "b.bean", 3)];
    expect(newLedgerErrors(before, after)).toEqual(after);
  });
});

describe("refuseNewLedgerErrors", () => {
  const balance = at(
    "Balance failed for Assets:Cash: expected 49.75 USD, got 73.25 USD",
    "main.bean",
    84,
  );

  it("never reads today's errors for a clean projection", async () => {
    const before = jest.fn(async () => []);
    await refuseNewLedgerErrors([], before, "delete");
    expect(before).not.toHaveBeenCalled();
  });

  it("refuses an introduced error, naming the write", async () => {
    await expect(
      refuseNewLedgerErrors([balance], async () => [], "delete"),
    ).rejects.toMatchObject({
      constructor: NewLedgerErrorsError,
      message:
        "this deletion would introduce 1 new bean-check error: Balance failed for Assets:Cash: expected 49.75 USD, got 73.25 USD (main.bean:84)",
      metadata: {
        code: "NEW_LEDGER_ERRORS",
        details: { count: 1, action: "delete" },
      },
    });
  });

  it("lets a write through that leaves only errors the ledger had", async () => {
    await expect(
      refuseNewLedgerErrors([balance], async () => [balance], "update"),
    ).resolves.toBeUndefined();
  });

  it("words a structured add as before", async () => {
    await expect(
      refuseNewLedgerErrors([balance], async () => [], "add"),
    ).rejects.toThrow(/^adding these entries would introduce 1 new/);
  });
});

// w21/188: the engine's warnings are not what bean-check refuses a write for.
describe("warnings and the write gate", () => {
  const warning = {
    message: "Transaction has only one posting",
    source: { filename: "main.bean", lineno: 90 },
    severity: "warning" as const,
  };

  it("does not count a new warning as a new error", () => {
    expect(newLedgerErrors([], [warning])).toEqual([]);
  });

  it("does not refuse a write that only adds a warning", async () => {
    const before = jest.fn(async () => []);
    await expect(
      refuseNewLedgerErrors([warning], before, "add" as never),
    ).resolves.toBeUndefined();
    expect(before).not.toHaveBeenCalled();
  });

  it("still refuses a real new error beside a warning", async () => {
    await expect(
      refuseNewLedgerErrors(
        [warning, { message: "does not balance", severity: "error" as const }],
        async () => [],
        "add" as never,
      ),
    ).rejects.toThrow();
  });
});
