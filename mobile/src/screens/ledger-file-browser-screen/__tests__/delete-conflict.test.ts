import fs from "fs";
import path from "path";
import { graphQLErrorCodes } from "../../../common/graphql-error-codes";
import {
  isConflictError,
  isConflictFailure,
} from "../../../common/ledger-conflict";

/**
 * w21/380: deleting a file that changed elsewhere toasted the server's raw "sha
 * does not match [given: …]" and never refreshed, so every retry sent the same
 * spent sha. Source checks for the screen.
 */
describe("deleting a file that changed elsewhere", () => {
  it("is recognised from the live message and from a CONFLICT code", () => {
    expect(
      isConflictError("sha does not match [given: 8f9f1c, expected: eeb8a2]"),
    ).toBe(true);
    const conflict = Object.assign(new Error("x"), {
      graphQLErrors: [{ message: "x", extensions: { code: "CONFLICT" } }],
    });
    expect(graphQLErrorCodes(conflict).includes("CONFLICT")).toBe(true);
    expect(isConflictFailure(conflict)).toBe(true);
    expect(
      isConflictFailure(
        new Error("sha does not match [given: a, expected: b]"),
      ),
    ).toBe(true);
    expect(isConflictFailure(new Error("Network request failed"))).toBe(false);
    expect(isConflictError("Network request failed")).toBe(false);
  });

  it("refreshes the list and says so in the user's language", () => {
    const src = fs
      .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
      .replace(/\s+/g, "");
    expect(src.includes("constchanged=isConflictFailure(deleteError);")).toBe(
      true,
    );
    expect(
      src.includes('if(changed)awaitinvalidateLedgerData(client,"file");'),
    ).toBe(true);
    expect(src.includes('t("ledgerDeleteFileChanged")')).toBe(true);
  });
});
