import fs from "fs";
import path from "path";
import { isLedgerGone } from "../../../common/graphql-error-codes";

/**
 * w21/378: a save after the file was deleted elsewhere ended in a bodiless
 * "Failed to save", and every retry failed the same way. Source checks: the
 * screen needs the native runtime.
 */
const notFound = Object.assign(new Error("Ledger resource not found"), {
  graphQLErrors: [{ message: "x", extensions: { code: "NOT_FOUND" } }],
});
const unavailable = Object.assign(new Error("Service unavailable"), {
  graphQLErrors: [
    { message: "x", extensions: { code: "SERVICE_UNAVAILABLE" } },
  ],
});
const screen = fs
  .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
  .replace(/\s+/g, "");

describe("saving a file that was deleted elsewhere", () => {
  it("is recognised by its NOT_FOUND code, not by other failures", () => {
    expect(isLedgerGone(notFound)).toBe(true);
    expect(isLedgerGone(unavailable)).toBe(false);
  });

  it("explains it and offers to copy the text or save it as a new file", () => {
    expect(screen.includes("}elseif(isLedgerGone(err)){")).toBe(true);
    expect(screen.includes('t("ledgerEditorFileGoneTitle")')).toBe(true);
    expect(
      screen.includes('{text:t("copy"),onPress:()=>voidcopyDraft(content)}'),
    ).toBe(true);
    expect(
      screen.includes("onPress:()=>voidrecreateFile(content,epoch,revision)"),
    ).toBe(true);
  });

  it("re-creates the file at the same path with the buffer and takes its sha", () => {
    expect(
      screen.includes("createLedgerFile({variables:{ledgerId,path,content:"),
    ).toBe(true);
    expect(
      screen.includes(
        "shaRef.current=newSha;recoveryRef.current.saved(content);",
      ),
    ).toBe(true);
  });

  it("never shows an alert with no body", () => {
    expect(
      screen.includes(
        'ledgerWriteFailureMessage(err,{t})??t("ledgerEditorSaveFailedHint")',
      ),
    ).toBe(true);
  });
});
