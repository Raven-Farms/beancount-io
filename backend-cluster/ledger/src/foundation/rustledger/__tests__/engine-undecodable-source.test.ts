/**
 * w23/011: a source file that is not UTF-8 text is parsed as an empty file,
 * and reported, naming it, only when the entry point's includes reach it. The
 * live WASM parse needs `--experimental-vm-modules` (see `loader.ts`), so the
 * engine is stubbed and records the FileMap it was handed.
 */
const parsed: Array<Record<string, string>> = [];
jest.mock("@/foundation/rustledger/loader", () => ({
  loadRustledger: async () => ({
    Ledger: {
      fromFiles: (files: Record<string, string>) => {
        parsed.push({ ...files });
        return {
          isValid: () => true,
          getErrors: () => [],
          getOptions: () => ({ title: null, operating_currencies: [] }),
          getDirectives: () => [],
          expandPads: () => ({
            directives: [],
            padding_transactions: [],
            errors: [],
          }),
          directiveCount: () => 0,
          free: () => undefined,
        };
      },
    },
  }),
}));

// Imported AFTER the mock so engine.ts picks up the stubbed loader.
import {
  clearLedgerSnapshotCache,
  parseLedgerFilesInProcess,
} from "@/foundation/rustledger/engine";
import { UNDECODABLE_SOURCE } from "@/foundation/rustledger/file-map-loader";

describe("parseLedgerFilesInProcess with an undecodable source file", () => {
  beforeEach(() => {
    clearLedgerSnapshotCache();
    parsed.length = 0;
  });

  it("ignores a file nothing includes and hands the engine no marker", async () => {
    const snapshot = await parseLedgerFilesInProcess(
      {
        "main.bean": "2024-01-01 open Assets:Cash USD\n",
        "export.bean": UNDECODABLE_SOURCE,
      },
      "main.bean",
    );
    expect(snapshot.valid).toBe(true);
    expect(snapshot.errors).toEqual([]);
    expect(parsed[0]?.["export.bean"]).toBe("");
  });

  it("reports an included one as a ledger error naming its path", async () => {
    const snapshot = await parseLedgerFilesInProcess(
      {
        "main.bean": 'include "imports/export.bean"\n',
        "imports/export.bean": UNDECODABLE_SOURCE,
      },
      "main.bean",
    );
    expect(snapshot.valid).toBe(false);
    expect(snapshot.errors).toEqual([
      expect.objectContaining({
        code: "INVALID_UTF8",
        severity: "error",
        file: "imports/export.bean",
        line: 1,
        message: expect.stringContaining("imports/export.bean"),
      }),
    ]);
    expect(parsed[0]?.["imports/export.bean"]).toBe("");
  });
});
