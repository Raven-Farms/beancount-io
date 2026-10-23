import fs from "fs";
import path from "path";
import { isWriteForbidden } from "../../../common/graphql-error-codes";
import { en } from "../../../translations/en";

/**
 * w21/474: a save after edit access was removed answered "Your text is still
 * here. Try again in a moment.", which can never succeed. Source checks for the
 * screen, which needs the native runtime.
 */
const withCode = (code: string) =>
  Object.assign(new Error("x"), {
    graphQLErrors: [{ message: "x", extensions: { code } }],
  });
const screen = fs
  .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
  .replace(/\s+/g, "");

describe("saving after edit access was removed", () => {
  it("is recognised by its FORBIDDEN code, not by a transient failure", () => {
    expect(isWriteForbidden(withCode("FORBIDDEN"))).toBe(true);
    expect(isWriteForbidden(withCode("SERVICE_UNAVAILABLE"))).toBe(false);
    expect(isWriteForbidden(withCode("INTERNAL_SERVER_ERROR"))).toBe(false);
    expect(isWriteForbidden(new Error("Network request failed"))).toBe(false);
    expect(isWriteForbidden(null)).toBe(false);
  });

  it("says edit access is gone and offers to copy the text, before the retry hint", () => {
    const forbidden = screen.indexOf("}elseif(isWriteForbidden(err)){");
    expect(forbidden > -1).toBe(true);
    expect(forbidden > screen.indexOf("}elseif(isLedgerGone(err)){")).toBe(
      true,
    );
    expect(forbidden < screen.indexOf('t("ledgerEditorSaveFailedHint")')).toBe(
      true,
    );
    const branch = screen.slice(forbidden, screen.indexOf("}else{", forbidden));
    expect(branch.includes('t("ledgerEditorAccessRemoved")')).toBe(true);
    expect(branch.includes("onPress:()=>voidcopyDraft(content)")).toBe(true);
    // Not told to try again.
    expect(branch.includes("ledgerEditorSaveFailedHint")).toBe(false);
  });

  it("has its message, in every language", () => {
    expect(en.ledgerEditorAccessRemoved.includes("no longer edit")).toBe(true);
    const dir = path.join(__dirname, "../../../translations");
    const missing = fs
      .readdirSync(dir)
      .filter((name) => /^[a-z]{2}\.ts$/.test(name))
      .filter(
        (name) =>
          !fs
            .readFileSync(path.join(dir, name), "utf8")
            .includes("ledgerEditorAccessRemoved:"),
      );
    expect(missing).toEqual([]);
  });
});
