import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";

// w21/297: a commit opened with no sha read as an empty commit ("No diff
// available." under a blank title), and a stale sha offered a Try Again that
// could never succeed. The screen runs hooks this runner cannot execute, so the
// wiring is checked on its source.
describe("the commit detail's missing and unknown commits", () => {
  const source = fs
    .readFileSync(
      path.join(__dirname, "..", "commit-detail-screen.tsx"),
      "utf8",
    )
    .replace(/\s+/g, "");

  it("redirects when no sha was given, before the ledger guard", () => {
    const redirect = source.indexOf(
      'if(!sha)return<Redirecthref="/(app)/(tabs)"/>;',
    );
    expect(redirect === -1).toBe(false);
    expect(redirect < source.indexOf("<LedgerGuard><CommitDetailRoute")).toBe(
      true,
    );
  });

  it("shows a gone state for NOT_FOUND instead of the retryable failure", () => {
    const gone = source.indexOf(
      'graphQLErrorCodes(error).includes("NOT_FOUND")',
    );
    expect(gone === -1).toBe(false);
    // Before the loading, failure and empty branches.
    expect(gone < source.indexOf("<CardLoadFailureonRetry")).toBe(true);
    expect(
      source.slice(gone, gone + 160).includes('t("commitDetailGone")'),
    ).toBe(true);
    expect(en.commitDetailGone).toBe("This commit is no longer available.");
  });
});
