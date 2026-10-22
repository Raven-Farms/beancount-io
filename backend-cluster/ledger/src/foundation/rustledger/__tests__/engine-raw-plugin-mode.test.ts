/**
 * Wiring test (w21/656): `option "plugin_processing_mode" "raw"` runs neither
 * Beancount's pad nor its balance step, but the engine accepts the option and
 * applies both. The live WASM parse needs `--experimental-vm-modules` (see
 * `loader.ts`), so the loader is stubbed with what rustledger 0.24 returns for
 * a pad, a failed balance and an account that was never opened; the live run
 * is in `scripts/verify-rustledger.ts`.
 */
const wasmError = (code: string, message: string) => ({
  message,
  code,
  phase: "validate",
  hint: null,
  file: "main.bean",
  line: 4,
  column: 1,
  end_line: null,
  end_column: null,
  severity: "error",
});

jest.mock("@/foundation/rustledger/loader", () => ({
  loadRustledger: async () => ({
    Ledger: {
      fromFiles: () => ({
        isValid: () => false,
        getErrors: () => [
          wasmError(
            "E2001",
            "Balance failed for Assets:Bank: expected 5 USD, got 100 USD",
          ),
          wasmError("E2003", "Unused Pad entry"),
          wasmError("E1001", "Account Assets:Nope was never opened"),
        ],
        getOptions: () => ({ title: null, operating_currencies: [] }),
        getDirectives: () => [],
        expandPads: () => ({
          directives: [
            {
              type: "pad",
              date: "2020-01-01",
              account: "Assets:Bank",
              source_account: "Equity:Open",
              meta: {},
            },
          ],
          padding_transactions: [
            {
              type: "transaction",
              date: "2020-01-01",
              flag: "P",
              payee: null,
              narration: "(Padding inserted for Balance of 100 USD)",
              tags: [],
              links: [],
              postings: [
                {
                  account: "Assets:Bank",
                  units: { number: "100", currency: "USD" },
                },
                {
                  account: "Equity:Open",
                  units: { number: "-100", currency: "USD" },
                },
              ],
              meta: {},
            },
          ],
          errors: [],
        }),
        directiveCount: () => 1,
        free: () => undefined,
      }),
    },
  }),
}));

// Imported AFTER the mock so engine.ts picks up the stubbed loader.
import {
  clearLedgerSnapshotCache,
  parseLedgerFilesInProcess,
} from "@/foundation/rustledger/engine";

const parse = (mode: string) =>
  parseLedgerFilesInProcess(
    {
      "main.bean": `option "plugin_processing_mode" "${mode}"\n2020-01-01 pad Assets:Bank Equity:Open\n`,
    },
    "main.bean",
    { repoPaths: ["main.bean"] },
  );

describe("parseLedgerFilesInProcess with raw plugin processing", () => {
  beforeEach(() => clearLedgerSnapshotCache());

  it("inserts no padding and checks no balance, but still validates", async () => {
    const snapshot = await parse("raw");
    expect(snapshot.directives.map((directive) => directive.type)).toEqual([
      "pad",
    ]);
    expect(snapshot.errors.map((error) => error.code)).toEqual(["E1001"]);
  });

  it("keeps both steps in the default mode", async () => {
    const snapshot = await parse("default");
    expect(snapshot.directives.map((directive) => directive.type)).toEqual([
      "pad",
      "transaction",
    ]);
    expect(snapshot.errors.map((error) => error.code)).toEqual([
      "E2001",
      "E2003",
      "E1001",
    ]);
  });
});
