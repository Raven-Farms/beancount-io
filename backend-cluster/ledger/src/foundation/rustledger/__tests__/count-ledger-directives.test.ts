/**
 * Directive counts are memoized by content (w0/m5). The live WASM parse needs
 * `--experimental-vm-modules` (see `loader.ts`), so the loader is stubbed with a
 * ledger that counts dated lines and records every parse.
 */
const parses: Record<string, string>[] = [];
let failNextParse = false;

jest.mock("@/foundation/rustledger/loader", () => ({
  loadRustledger: async () => ({
    Ledger: {
      fromFiles: (files: Record<string, string>) => {
        if (failNextParse) {
          failNextParse = false;
          throw new Error("parse failed");
        }
        parses.push(files);
        return {
          directiveCount: () =>
            Object.values(files)
              .join("\n")
              .split("\n")
              .filter((line) => /^\d{4}-\d{2}-\d{2} /u.test(line)).length,
          free: () => undefined,
        };
      },
    },
  }),
}));

import { countLedgerDirectives } from "../engine";

let n = 0;
/** A ledger no other test has counted, with `extra` more directives. */
function ledger(extra = 0): Record<string, string> {
  n += 1;
  const lines = [`2024-01-01 open Assets:Unique${n} USD`];
  for (let i = 0; i < extra; i += 1) {
    lines.push(`2024-01-02 open Assets:Extra${n}x${i} USD`);
  }
  return { "main.bean": `${lines.join("\n")}\n` };
}

beforeEach(() => {
  parses.length = 0;
});

describe("countLedgerDirectives", () => {
  it("parses a ledger once however many times it is counted", async () => {
    const files = ledger(2);

    await expect(countLedgerDirectives(files, "main.bean")).resolves.toBe(3);
    await expect(countLedgerDirectives(files, "main.bean")).resolves.toBe(3);

    expect(parses).toHaveLength(1);
  });

  it("serves the next write's committed ledger from the last write's projection", async () => {
    // The map a write projects becomes the committed map the next write loads:
    // a different object with the same content.
    const projected = ledger(1);
    await countLedgerDirectives(projected, "main.bean");
    const committedNext = { ...projected };

    await expect(
      countLedgerDirectives(committedNext, "main.bean"),
    ).resolves.toBe(2);
    expect(parses).toHaveLength(1);
  });

  it("parses again when the content changes", async () => {
    const before = ledger();
    await countLedgerDirectives(before, "main.bean");
    const after = {
      "main.bean": `${before["main.bean"]}2024-01-03 open Assets:New USD\n`,
    };

    await expect(countLedgerDirectives(after, "main.bean")).resolves.toBe(2);
    expect(parses).toHaveLength(2);
  });

  it("does not remember a failed count", async () => {
    const files = ledger();
    failNextParse = true;

    await expect(countLedgerDirectives(files, "main.bean")).rejects.toThrow(
      "parse failed",
    );
    await expect(countLedgerDirectives(files, "main.bean")).resolves.toBe(1);
    expect(parses).toHaveLength(1);
  });
});
