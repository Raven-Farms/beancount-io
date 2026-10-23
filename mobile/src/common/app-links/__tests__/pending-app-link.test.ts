import fs from "fs";
import path from "path";
import {
  clearPendingAppLink,
  peekPendingAppLink,
  routeIncomingAppLink,
  setPendingAppLink,
  takePendingAppLink,
} from "../pending-app-link";
import { rewriteSystemPath } from "../rewrite-system-path";

describe("pendingAppLink", () => {
  afterEach(() => {
    clearPendingAppLink();
  });

  it("stores a target and consumes it once after sign-in", () => {
    const target = {
      ledgerFullName: "open_ledger/example",
      href: "/reports" as const,
    };
    const sourceUrl =
      "https://beancount.io/ledger/open_ledger/example/balance-sheet";
    setPendingAppLink(target, sourceUrl);
    expect(peekPendingAppLink()).toEqual({ target, sourceUrl });
    expect(takePendingAppLink()).toEqual({ target, sourceUrl });
    expect(takePendingAppLink()).toBe(null);
  });
});

// w21/083: a link opened while signed in stayed stashed and replayed on the
// next sign-in, possibly as another account.
describe("a link opened while signed in", () => {
  afterEach(() => {
    clearPendingAppLink();
  });

  const url = "https://beancount.io/ledger/alice/books/journal";

  it("opens now and leaves nothing to replay", () => {
    // `+native-intent` stashes every link it resolves, session or not.
    rewriteSystemPath(url);
    const stashed = peekPendingAppLink();
    expect(stashed === null).toBe(false);
    expect(routeIncomingAppLink(stashed!.target, url, true)).toBe(true);
    expect(peekPendingAppLink()).toBe(null);
    // The next session change finds nothing to open.
    expect(takePendingAppLink()).toBe(null);
  });

  it("still waits for sign-in when signed out", () => {
    rewriteSystemPath(url);
    const target = peekPendingAppLink()!.target;
    clearPendingAppLink();
    expect(routeIncomingAppLink(target, url, false)).toBe(false);
    expect(peekPendingAppLink()).toEqual({ target, sourceUrl: url });
  });

  it("is routed by the handler and cleared on sign-out", () => {
    const read = (...parts: string[]) =>
      fs.readFileSync(path.join(__dirname, "..", ...parts), "utf8");
    expect(
      read("use-app-link-handler.ts").includes(
        "if (routeIncomingAppLink(target, candidate, !!sessionRef.current)) {",
      ),
    ).toBe(true);
    expect(
      read("..", "server-url-actions.ts").includes("  clearPendingAppLink();"),
    ).toBe(true);
  });
});
