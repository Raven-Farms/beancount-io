import { buildLedgerUrl, type BuildLedgerUrlInput } from "../build-ledger-url";
import { resolveAppLink } from "../resolve-app-link";

const LEDGER = "open_ledger/example";
const ORIGIN = "https://beancount.io";

describe("resolveAppLink", () => {
  it("maps ledger home and overview to the tabs root", () => {
    expect(
      resolveAppLink(`${ORIGIN}/ledger/${LEDGER}`, { serverUrl: ORIGIN }),
    ).toEqual({ ledgerFullName: LEDGER, href: "/" });
    expect(
      resolveAppLink(`${ORIGIN}/ledger/${LEDGER}/overview/`, {
        serverUrl: ORIGIN,
      }),
    ).toEqual({ ledgerFullName: LEDGER, href: "/" });
  });

  it("maps each documented ledger sub-path", () => {
    expect(
      resolveAppLink(`${ORIGIN}/ledger/${LEDGER}/account/Assets:Cash`, {
        serverUrl: ORIGIN,
      }),
    ).toEqual({
      ledgerFullName: LEDGER,
      href: {
        pathname: "/account-detail",
        params: { account: "Assets:Cash", ledger: LEDGER },
      },
    });
    expect(
      resolveAppLink(`${ORIGIN}/ledger/${LEDGER}/journal`, {
        serverUrl: ORIGIN,
      }),
    ).toEqual({
      ledgerFullName: LEDGER,
      href: "/transactions",
      filters: { statuses: [], range: "all" },
    });
    expect(
      resolveAppLink(`${ORIGIN}/ledger/${LEDGER}/commit/abc123`, {
        serverUrl: ORIGIN,
      }),
    ).toEqual({
      ledgerFullName: LEDGER,
      href: {
        pathname: "/commit-detail",
        params: { sha: "abc123", ledger: LEDGER },
      },
    });
    expect(
      resolveAppLink(
        `${ORIGIN}/ledger/${LEDGER}/files/blob/main/main.beancount`,
        { serverUrl: ORIGIN },
      ),
    ).toEqual({
      ledgerFullName: LEDGER,
      href: {
        pathname: "/ledger-file-editor",
        // Bound to the link's ledger (w21/199).
        params: { path: "main.beancount", ledger: LEDGER },
      },
    });
    expect(
      resolveAppLink(`${ORIGIN}/ledger/${LEDGER}/balance-sheet`, {
        serverUrl: ORIGIN,
      }),
    ).toEqual({
      ledgerFullName: LEDGER,
      href: "/reports",
    });
    expect(
      resolveAppLink(`${ORIGIN}/ledger/${LEDGER}/income-statement`, {
        serverUrl: ORIGIN,
      }),
    ).toEqual({
      ledgerFullName: LEDGER,
      href: "/reports",
    });
    expect(
      resolveAppLink(`${ORIGIN}/ledger/${LEDGER}/budget`, {
        serverUrl: ORIGIN,
      }),
    ).toEqual({ ledgerFullName: LEDGER, href: "/budget" });
    expect(
      resolveAppLink(`${ORIGIN}/ledger/${LEDGER}/entry/deadbeef`, {
        serverUrl: ORIGIN,
      }),
    ).toEqual({
      ledgerFullName: LEDGER,
      href: {
        pathname: "/transaction-detail",
        params: { entry_hash: "deadbeef", ledger: LEDGER },
      },
    });
  });

  it("falls unknown sub-paths back to ledger home", () => {
    expect(
      resolveAppLink(`${ORIGIN}/ledger/${LEDGER}/holdings`, {
        serverUrl: ORIGIN,
      }),
    ).toEqual({ ledgerFullName: LEDGER, href: "/" });
  });

  it("decodes encoded account names and ignores query strings", () => {
    expect(
      resolveAppLink(
        `${ORIGIN}/ledger/${LEDGER}/account/Assets%3ABank%20Checking?lang=en`,
        { serverUrl: ORIGIN },
      ),
    ).toEqual({
      ledgerFullName: LEDGER,
      href: {
        pathname: "/account-detail",
        params: { account: "Assets:Bank Checking", ledger: LEDGER },
      },
    });
  });

  it("rejects non-ledger and foreign-host URLs", () => {
    expect(resolveAppLink(`${ORIGIN}/gallery`, { serverUrl: ORIGIN })).toBe(
      null,
    );
    expect(
      resolveAppLink(`${ORIGIN}/auth/sign-in`, { serverUrl: ORIGIN }),
    ).toBe(null);
    expect(
      resolveAppLink("https://evil.example/ledger/open_ledger/example", {
        serverUrl: ORIGIN,
      }),
    ).toBe(null);
    expect(resolveAppLink("not-a-url")).toBe(null);
  });

  it("accepts the selected server's host, and the hosted domain only when it is the server", () => {
    const selfHost = "https://books.example.test";
    expect(
      resolveAppLink(`${selfHost}/ledger/${LEDGER}/journal`, {
        serverUrl: selfHost,
      }),
    ).toEqual({
      ledgerFullName: LEDGER,
      href: "/transactions",
      filters: { statuses: [], range: "all" },
    });
    // A beancount.io link is the hosted service's ledger, not the same-named
    // one on the selected self-hosted server (w21/348).
    expect(
      resolveAppLink(`${ORIGIN}/ledger/${LEDGER}`, { serverUrl: selfHost }),
    ).toBe(null);
    expect(resolveAppLink(`${ORIGIN}/ledger/${LEDGER}`)).toEqual({
      ledgerFullName: LEDGER,
      href: "/",
    });
  });
});

describe("buildLedgerUrl round trip", () => {
  const cases: BuildLedgerUrlInput[] = [
    { kind: "home", ledgerFullName: LEDGER },
    { kind: "account", ledgerFullName: LEDGER, account: "Assets:Cash" },
    { kind: "journal", ledgerFullName: LEDGER },
    { kind: "accounts", ledgerFullName: LEDGER },
    { kind: "open-account", ledgerFullName: LEDGER },
    { kind: "new-entry", ledgerFullName: LEDGER },
    { kind: "files", ledgerFullName: LEDGER },
    { kind: "commit", ledgerFullName: LEDGER, sha: "abc123" },
    {
      kind: "file",
      ledgerFullName: LEDGER,
      branch: "main",
      path: "accounts/bank.beancount",
    },
    { kind: "income-statement", ledgerFullName: LEDGER },
    { kind: "balance-sheet", ledgerFullName: LEDGER },
    { kind: "budget", ledgerFullName: LEDGER },
    { kind: "entry", ledgerFullName: LEDGER, entryHash: "deadbeef" },
  ];

  for (const input of cases) {
    it(`round-trips ${input.kind}`, () => {
      const url = buildLedgerUrl(input, ORIGIN);
      const resolved = resolveAppLink(url, { serverUrl: ORIGIN });
      expect(resolved === null).toBe(false);
      expect(resolved!.ledgerFullName).toBe(LEDGER);
      // income-statement and balance-sheet both land on reports.
      if (input.kind === "income-statement" || input.kind === "balance-sheet") {
        expect(resolved!.href).toBe("/reports");
        return;
      }
      if (input.kind === "home") {
        expect(resolved!.href).toBe("/");
        return;
      }
      if (input.kind === "journal") {
        expect(resolved!.href).toBe("/transactions");
        return;
      }
      if (input.kind === "accounts") {
        expect(resolved!.href).toBe("/accounts");
        return;
      }
      if (input.kind === "open-account") {
        expect(resolved!.href).toBe("/open-account");
        return;
      }
      if (input.kind === "new-entry") {
        expect(resolved!.href).toBe("/add-transaction");
        return;
      }
      if (input.kind === "files") {
        expect(resolved!.href).toBe("/ledger");
        return;
      }
      if (input.kind === "budget") {
        expect(resolved!.href).toBe("/budget");
        return;
      }
      if (input.kind === "account") {
        expect(resolved!.href).toEqual({
          pathname: "/account-detail",
          params: { account: input.account, ledger: LEDGER },
        });
        return;
      }
      if (input.kind === "commit") {
        expect(resolved!.href).toEqual({
          pathname: "/commit-detail",
          params: { sha: input.sha, ledger: LEDGER },
        });
        return;
      }
      if (input.kind === "file") {
        expect(resolved!.href).toEqual({
          pathname: "/ledger-file-editor",
          params: { path: input.path, ledger: LEDGER },
        });
        return;
      }
      if (input.kind === "entry") {
        expect(resolved!.href).toEqual({
          pathname: "/transaction-detail",
          params: { entry_hash: input.entryHash, ledger: LEDGER },
        });
      }
    });
  }

  // w21/223: the dashboard's ledger-errors table links to the error's line.
  describe("a file link with a line number", () => {
    const file = `${ORIGIN}/ledger/${LEDGER}/files/blob/main/main.bean`;
    const params = (url: string) =>
      (
        resolveAppLink(url, { serverUrl: ORIGIN })?.href as {
          params: Record<string, string>;
        }
      ).params;

    it("opens the editor at that line", () => {
      expect(params(`${file}?lineNumber=42`)).toEqual({
        path: "main.bean",
        ledger: LEDGER,
        initialLine: "42",
      });
    });

    it("ignores a line that is not a positive whole number", () => {
      for (const bad of [
        "0",
        "-3",
        "4.5",
        "abc",
        "",
        "1e3",
        "07x",
        "9999999999",
      ]) {
        expect(params(`${file}?lineNumber=${bad}`)).toEqual({
          path: "main.bean",
          ledger: LEDGER,
        });
      }
      expect(params(file)).toEqual({ path: "main.bean", ledger: LEDGER });
    });
  });
});

// w21/545: the dashboard's errors, commits, cash-flow and trial-balance pages
// all opened Home.
describe("dashboard pages with a matching screen", () => {
  const open = (page: string) =>
    resolveAppLink(`${ORIGIN}/ledger/${LEDGER}/${page}`, {
      serverUrl: ORIGIN,
    });

  it("opens Notifications for errors and commits", () => {
    expect(open("errors")).toEqual({
      ledgerFullName: LEDGER,
      href: "/notifications",
    });
    expect(open("commits")).toEqual({
      ledgerFullName: LEDGER,
      href: "/notifications",
    });
  });

  it("opens Reports for cash-flow and trial-balance", () => {
    expect(open("cash-flow")).toEqual({
      ledgerFullName: LEDGER,
      href: "/reports",
    });
    expect(open("trial-balance")).toEqual({
      ledgerFullName: LEDGER,
      href: "/reports",
    });
  });

  it("still opens Home for a page the app has no screen for", () => {
    expect(open("holdings")).toEqual({ ledgerFullName: LEDGER, href: "/" });
  });
});
