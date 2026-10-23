/**
 * New Transaction keeps a refused save's reason on screen (w21/001). The
 * outcomes come from the real write helper, so a refused `addEntries`, a
 * payload rejection and an offline failure are each what the screen gets.
 *
 * Relative requires: the runner has no `@/` alias for value imports.
 */
import fs from "fs";
import path from "path";
import { describeLedgerRefusal } from "../../../common/ledger-refusal";
import { runLedgerWrite } from "../../../common/ledger-write";
import { inlineSaveError } from "../inline-save-error";

const BALANCE_FAILED =
  "Balance failed for Assets:Cash: expected 49.75 USD, got 44.75 USD (main.bean:87)";
const i18n = {
  t: (_key: "ledgerWouldBreak", { detail }: { detail: string }) =>
    `This would add an error to your ledger: ${detail}`,
};

const save = (perform: () => Promise<{ success: boolean }>) =>
  runLedgerWrite(
    {
      showToast: () => () => undefined,
      haptics: { success: () => undefined, error: () => undefined },
      goBack: () => undefined,
      describeRefusal: (error) => describeLedgerRefusal(error, i18n),
    },
    {
      perform,
      didSucceed: (result) => result.success,
      successMessage: "Saved",
      failureMessage: "Couldn't save",
      goBackOnSuccess: false,
    },
  );

describe("inlineSaveError", () => {
  it("keeps a refused entry's reason", async () => {
    const outcome = await save(async () => {
      throw Object.assign(new Error("Validation failed for entries"), {
        graphQLErrors: [
          {
            message: "Validation failed",
            extensions: {
              code: "VALIDATION_FAILED",
              field: "entries",
              newLedgerErrors: BALANCE_FAILED,
            },
          },
        ],
      });
    });
    expect(inlineSaveError(outcome)).toBe(
      `This would add an error to your ledger: ${BALANCE_FAILED}`,
    );
  });

  it("keeps a generic failure's message the same way", async () => {
    const offline = await save(async () => {
      throw new Error("Network request failed");
    });
    expect(inlineSaveError(offline)).toBe("Couldn't save");
    const rejected = await save(async () => ({ success: false }));
    expect(inlineSaveError(rejected)).toBe("Couldn't save");
  });

  it("shows nothing after a save that went through", async () => {
    expect(inlineSaveError(await save(async () => ({ success: true })))).toBe(
      null,
    );
  });
});

describe("New Transaction", () => {
  it("renders the save's outcome under the postings", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "multi-postings-transaction-screen.tsx"),
      "utf8",
    );
    expect(source.includes("setSaveError(inlineSaveError(outcome))")).toBe(
      true,
    );
    expect(source.includes('testID="new-transaction-save-error"')).toBe(true);
  });
});
