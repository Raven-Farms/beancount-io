import fs from "fs";
import path from "path";
import type { DirectiveJson } from "@rustledger/wasm";
import {
  failedBalanceDiffs,
  serializeDirective,
} from "@/foundation/rustledger/journal-serialize";

/**
 * w21/087: rustledger's `DirectiveJson` has no failed-assertion diff, so every
 * Balance row went out with `diff_amount: null` and a failing assertion looked
 * exactly like a passing one. The validator's E2001 error carries both
 * amounts; this joins it back. Error shapes are the engine's own output for
 * the note's fixture (`Balance failed for …: expected …, got …`).
 */
const balance = (date: string, account: string, number: string) =>
  ({
    type: "balance",
    date,
    account,
    amount: { number, currency: "USD" },
    meta: {},
  }) as unknown as DirectiveJson;

const failed = (
  account: string,
  expected: string,
  got: string,
  line: number,
) => ({
  message: `Balance failed for ${account}: expected ${expected} USD, got ${got} USD`,
  code: "E2001",
  file: "main.bean",
  line,
});

describe("failedBalanceDiffs", () => {
  it("gives a failing assertion actual − expected and leaves a passing one null", () => {
    const passing = balance("2026-08-29", "Assets:Cash", "49.75");
    const failing = balance("2026-10-01", "Assets:Cash", "50.00");
    const diffs = failedBalanceDiffs(
      [passing, failing],
      [failed("Assets:Cash", "50.00", "49.75", 8)],
    );
    expect(serializeDirective(failing, diffs)).toMatchObject({
      diff_amount: { number: "-0.25", currency: "USD" },
    });
    expect(serializeDirective(passing, diffs)).toMatchObject({
      diff_amount: null,
    });
  });

  it("matches an amount however it was written", () => {
    const failing = balance("2026-10-01", "Assets:Cash", "50");
    const diffs = failedBalanceDiffs(
      [failing],
      [failed("Assets:Cash", "50.00", "52.5", 3)],
    );
    expect(diffs.get(failing)).toEqual({ number: "2.50", currency: "USD" });
  });

  it("marks nothing when it cannot tell which same-amount assertion failed", () => {
    const first = balance("2026-09-01", "Assets:Cash", "50.00");
    const second = balance("2026-10-01", "Assets:Cash", "50.00");
    const diffs = failedBalanceDiffs(
      [first, second],
      [failed("Assets:Cash", "50.00", "49.75", 9)],
    );
    expect(diffs.size).toBe(0);
  });

  it("pairs several failures of one amount with their assertions in order", () => {
    const first = balance("2026-09-01", "Assets:Cash", "50.00");
    const second = balance("2026-10-01", "Assets:Cash", "50.00");
    const diffs = failedBalanceDiffs(
      [second, first],
      [
        failed("Assets:Cash", "50.00", "48.00", 12),
        failed("Assets:Cash", "50.00", "49.75", 9),
      ],
    );
    expect(diffs.get(first)).toEqual({ number: "-0.25", currency: "USD" });
    expect(diffs.get(second)).toEqual({ number: "-2.00", currency: "USD" });
  });

  it("ignores other errors", () => {
    const failing = balance("2026-10-01", "Assets:Cash", "50.00");
    const diffs = failedBalanceDiffs(
      [failing],
      [
        { message: "Transaction does not balance", code: "E3001" },
        {
          message:
            "Balance failed for Assets:Cash: expected 50.00 USD, got 49.75 USD",
          code: null,
        },
      ],
    );
    expect(diffs.size).toBe(0);
  });
});

describe("journal reads", () => {
  // REST, GraphQL and MCP all read the journal through these: the service's
  // journal, account journal and entry context, and the V1 legacy route.
  const read = (file: string) =>
    fs.readFileSync(path.join(__dirname, "..", "..", "..", file), "utf8");

  it("pass the validator's diffs to the serializer", () => {
    const service = read("features/ledger/service/ledger-journal-service.ts");
    expect(
      service.match(/failedBalanceDiffs\(/g)?.length ?? 0,
    ).toBeGreaterThanOrEqual(3);
    expect(service).toContain("serializeDirective(directive, balanceDiffs)");
    expect(read("api/legacy.ts")).toContain(
      "failedBalanceDiffs(snapshot.directives, snapshot.errors)",
    );
  });
});
