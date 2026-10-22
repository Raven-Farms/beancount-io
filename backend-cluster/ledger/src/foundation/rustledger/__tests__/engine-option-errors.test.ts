/**
 * Wiring test (w21/308): a parse reports Beancount's own default options
 * without red errors. The live WASM parse needs `--experimental-vm-modules`
 * (see `loader.ts`), so the loader is stubbed with the errors rustledger 0.24
 * returns for `option "account_previous_balances" "Opening-Balances"` and
 * `option "account_rounding" "Rounding"`; the live run is in
 * `scripts/verify-rustledger.ts`.
 */
const wasmError = (message: string) => ({
  message,
  code: null,
  phase: null,
  hint: null,
  file: null,
  line: null,
  column: null,
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
          wasmError("[E7002] Invalid leaf account name: 'Opening-Balances'"),
          wasmError("[E7002] Invalid leaf account name: 'Rounding'"),
          wasmError(
            "[E7007] Option 'account_rounding' is accepted for compatibility but has no effect: no rounding residual is produced.",
          ),
          wasmError("[E7002] Invalid leaf account name: 'rounding'"),
        ],
        getOptions: () => ({ title: null, operating_currencies: [] }),
        getDirectives: () => [],
        expandPads: () => ({
          directives: [],
          padding_transactions: [],
          errors: [],
        }),
        directiveCount: () => 0,
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

describe("parseLedgerFilesInProcess with Beancount's default options", () => {
  beforeEach(() => clearLedgerSnapshotCache());

  it("drops the valid-leaf errors, warns for E7007 and keeps a real one", async () => {
    const snapshot = await parseLedgerFilesInProcess(
      {
        "main.bean":
          'option "account_previous_balances" "Opening-Balances"\noption "account_rounding" "Rounding"\n',
      },
      "main.bean",
      { repoPaths: ["main.bean"] },
    );
    expect(
      snapshot.errors.map((error) => [
        error.severity,
        error.message.slice(0, 7),
      ]),
    ).toEqual([
      ["warning", "[E7007]"],
      ["error", "[E7002]"],
    ]);
    // The genuinely invalid leaf is still an error, so the ledger is invalid.
    expect(snapshot.valid).toBe(false);
  });
});
