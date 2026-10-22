import fs from "fs";
import path from "path";
import { isPluginCopy } from "../select-plugin-copy";
import { shouldShowTransactionWriteActions } from "../select-transaction-write-actions";

// w21/443: an amortize_over or forecast copy answers with its template's slice
// and checksum, so Delete on it removed the whole series.
const TEMPLATE = [
  '2026-06-01 * "QA Insurer" "car insurance"',
  '  amortize_months: "12"',
  "  Expenses:Insurance  600.00 USD",
  "  Assets:Bank",
].join("\n");

describe("isPluginCopy", () => {
  it("is true for each amortized copy, the first included", () => {
    // (1/12) shares the template's day; its name is what differs.
    expect(
      isPluginCopy(
        {
          date: "2026-06-01",
          payee: "QA Insurer",
          narration: "car insurance (1/12)",
        },
        TEMPLATE,
      ),
    ).toBe(true);
    expect(
      isPluginCopy(
        {
          date: "2026-09-01",
          payee: "QA Insurer",
          narration: "car insurance (4/12)",
        },
        TEMPLATE,
      ),
    ).toBe(true);
  });

  it("is true for a forecast occurrence, whose marker the template carries", () => {
    const slice = '2026-06-01 # "Power [MONTHLY REPEAT 3 TIMES]"\n  A  1 USD';
    expect(
      isPluginCopy({ date: "2026-06-01", narration: "Power" }, slice),
    ).toBe(true);
    expect(
      isPluginCopy({ date: "2026-07-01", narration: "Power" }, slice),
    ).toBe(true);
  });

  it("is false for an entry that is its own text", () => {
    expect(
      isPluginCopy(
        {
          date: "2026-06-01T00:00:00",
          payee: "QA Insurer",
          narration: "car insurance",
        },
        TEMPLATE,
      ),
    ).toBe(false);
    // Narration only, payee absent or null, a flag other than `*`, `txn`.
    for (const header of [
      '2026-08-06 * "Lunch"',
      '2026-08-06 ! "Lunch"',
      '2026-08-06 txn "Lunch"',
      '; note\n2026-08-06 * "Lunch" #trip ^receipt',
    ]) {
      expect(
        isPluginCopy(
          { date: "2026-08-06", payee: null, narration: "Lunch" },
          header,
        ),
      ).toBe(false);
    }
    // No narration at all.
    expect(
      isPluginCopy({ date: "2026-08-06", narration: "" }, "2026-08-06 *"),
    ).toBe(false);
  });

  it("does not judge what it cannot read", () => {
    const entry = { date: "2026-08-06", narration: "Lunch" };
    expect(isPluginCopy(entry, undefined)).toBe(false);
    expect(isPluginCopy(entry, "")).toBe(false);
    expect(isPluginCopy(entry, "not a directive")).toBe(false);
    // An escape in the written string is not compared.
    expect(
      isPluginCopy(
        { date: "2026-08-06", narration: 'He said "hi"' },
        '2026-08-06 * "He said \\"hi\\""',
      ),
    ).toBe(false);
  });

  it("is true when the slice is another kind of directive (a pad)", () => {
    expect(
      isPluginCopy(
        { date: "2026-08-06", narration: "(Padding inserted)" },
        "2026-08-06 pad Assets:Cash Equity:Opening-Balances",
      ),
    ).toBe(true);
  });
});

describe("the write actions", () => {
  it("are withheld from a copy, whatever the write access", () => {
    expect(shouldShowTransactionWriteActions(true, "sha", false)).toBe(true);
    expect(shouldShowTransactionWriteActions(true, "sha", true)).toBe(false);
    expect(shouldShowTransactionWriteActions(true, "sha")).toBe(true);
    expect(shouldShowTransactionWriteActions(false, "sha", false)).toBe(false);
  });

  it("are decided by the screen with the entry and its slice", () => {
    const source = fs
      .readFileSync(
        path.join(__dirname, "..", "..", "transaction-detail-screen.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(
      source.includes(
        "shouldShowTransactionWriteActions(canWrite,sha256sum,isPluginCopy(entry,contextSource?.slice),)",
      ),
    ).toBe(true);
  });
});
