import {
  capBqlText,
  executeBqlQuery,
  executeStructuredBqlQuery,
  MAX_BQL_TEXT_BYTES,
  MAX_STRUCTURED_BQL_ROWS,
} from "../bql-query-tool";
import { BQL_ROW_COUNT, BQL_TRUNCATED } from "../bql-result-metadata";
import type { ToolContext } from "../types";

/**
 * w2/m28:t001. A `SELECT` with no `LIMIT` over a real ledger is tens of
 * thousands of postings, all of which used to arrive in the model's context
 * whether it needed the tail or not — and with no way to tell whether it had
 * seen the whole result.
 */
function ctx(rows: unknown[][]) {
  const queryShell = jest.fn(async () => ({
    resultType: "table" as const,
    table: {
      types: [{ name: "account", dtype: "str" }],
      rows,
    },
  }));
  return {
    queryShell,
    context: {
      services: { ledgerShell: { queryShell } },
      identity: { userId: "usr_1" },
      ledgerId: "alice/main",
    } as unknown as Pick<ToolContext, "services" | "identity" | "ledgerId">,
  };
}

const rows = (count: number) =>
  Array.from({ length: count }, (_, i) => [`Assets:A${i}`]);

describe("runBqlQueryStructured", () => {
  it("reports how many rows came back", async () => {
    const { context } = ctx(rows(3));
    const result = await executeStructuredBqlQuery(context, { query: "x" });
    expect(result).toMatchObject({
      ok: true,
      result: { rowCount: 3, truncated: false },
    });
  });

  it("counts an empty result as zero rather than omitting the count", async () => {
    const { context } = ctx([]);
    const result = await executeStructuredBqlQuery(context, { query: "x" });
    expect(result.ok && result.result.rowCount).toBe(0);
    expect(result.ok && result.result.truncated).toBe(false);
  });

  it("caps a runaway result and says that it did", async () => {
    const { context } = ctx(rows(MAX_STRUCTURED_BQL_ROWS + 500));
    const result = await executeStructuredBqlQuery(context, { query: "x" });
    expect(result.ok && result.result.truncated).toBe(true);
    expect(result.ok && result.result.rowCount).toBe(MAX_STRUCTURED_BQL_ROWS);
    expect(result.ok && result.result.table?.rows).toHaveLength(
      MAX_STRUCTURED_BQL_ROWS,
    );
  });

  it("leaves a text result alone, with nothing to count", async () => {
    const queryShell = jest.fn(async () => ({
      resultType: "text" as const,
      text: { contents: "No matching entries\n" },
    }));
    const result = await executeStructuredBqlQuery(
      {
        services: { ledgerShell: { queryShell } },
        identity: { userId: "usr_1" },
        ledgerId: "alice/main",
      } as unknown as Pick<ToolContext, "services" | "identity" | "ledgerId">,
      { query: "x" },
    );
    expect(result).toMatchObject({
      ok: true,
      result: {
        resultType: "text",
        rowCount: 0,
        truncated: false,
        text: { contents: "No matching entries\n" },
      },
    });
  });

  it("returns the failure as a value rather than throwing", async () => {
    const queryShell = jest.fn(async () => {
      throw new Error("Fava is down");
    });
    const result = await executeStructuredBqlQuery(
      {
        services: { ledgerShell: { queryShell } },
        identity: { userId: "usr_1" },
        ledgerId: "alice/main",
      } as unknown as Pick<ToolContext, "services" | "identity" | "ledgerId">,
      { query: "x" },
    );
    expect(result).toMatchObject({ ok: false, error: "Fava is down" });
  });
});

/**
 * w23/010. `runBqlQuery` returned the shell's whole text: one `JOURNAL` over a
 * 3,209-posting ledger was 5 MB in the model's context.
 */
describe("runBqlQuery text ceiling", () => {
  const header = "account\n-------\n";

  it("returns text under both ceilings unchanged", () => {
    const text = `${header}${"Assets:Cash\n".repeat(MAX_STRUCTURED_BQL_ROWS)}`;
    expect(capBqlText(text)).toEqual({ text, truncated: false });
  });

  it("keeps the header and the first 1000 rows of a longer table", () => {
    const rows = Array.from({ length: 1500 }, (_, i) => `row-${i}`);
    const { text, truncated } = capBqlText(`${header}${rows.join("\n")}\n`);
    const lines = text.trimEnd().split("\n");
    expect(truncated).toBe(true);
    expect(lines.slice(0, 2)).toEqual(["account", "-------"]);
    expect(lines[1001]).toBe("row-999");
    expect(lines).toHaveLength(1003);
    expect(lines[1002]).toMatch(
      /^\[truncated: showing the first 1002 of 1502 lines/,
    );
  });

  it("cuts wide rows at a line boundary under the byte ceiling", () => {
    // Forty 4 KB lines, each with a multi-byte character: ~160 KB.
    const wide = `${"é".repeat(2000)}`;
    const source = Array.from({ length: 40 }, () => wide).join("\n");
    const { text, truncated } = capBqlText(source);
    expect(truncated).toBe(true);
    expect(Buffer.byteLength(text)).toBeLessThan(MAX_BQL_TEXT_BYTES + 300);
    const lines = text.trimEnd().split("\n");
    // Every kept line is whole; only the marker follows them.
    expect(lines.slice(0, -1).every((line) => line === wide)).toBe(true);
    expect(lines.at(-1)).toContain(`of ${Buffer.byteLength(source)} bytes`);
  });

  it("marks the result it cut, keeping the canonical row count", async () => {
    const queryShellText = jest.fn(async () => ({
      text: `${header}${"Assets:Cash\n".repeat(3209)}`,
      rowCount: 3209,
    }));
    const result = await executeBqlQuery(
      {
        services: { ledgerShell: { queryShellText } },
        identity: { userId: "usr_1" },
        ledgerId: "alice/main",
      } as unknown as Pick<ToolContext, "services" | "identity" | "ledgerId">,
      { query: "SELECT account" },
    );
    expect(result.ok).toBe(true);
    expect(Reflect.get(result, BQL_ROW_COUNT)).toBe(3209);
    expect(Reflect.get(result, BQL_TRUNCATED)).toBe(true);
    if (result.ok) expect(result.result).toContain("[truncated:");
  });
});
