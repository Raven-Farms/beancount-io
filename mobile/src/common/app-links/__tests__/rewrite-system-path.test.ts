import fs from "fs";
import path from "path";
import { resolveAppLink } from "../resolve-app-link";
import {
  browserFallbackUrl,
  hrefToPath,
  rewriteSystemPath,
} from "../rewrite-system-path";
import { clearPendingAppLink, takePendingAppLink } from "../pending-app-link";

describe("rewriteSystemPath", () => {
  afterEach(() => {
    clearPendingAppLink();
  });

  it("rewrites a ledger balance-sheet path to reports and stashes the target", () => {
    const path = "/ledger/open_ledger/example/balance-sheet";
    const rewritten = rewriteSystemPath(path);
    expect(rewritten).toBe("/reports");
    const pending = takePendingAppLink();
    expect(pending?.target.ledgerFullName).toBe("open_ledger/example");
    expect(pending?.target.href).toBe("/reports");
  });

  it("rewrites custom-scheme ledger paths the same way", () => {
    clearPendingAppLink();
    expect(
      rewriteSystemPath(
        "beancount:///ledger/open_ledger/example/balance-sheet",
      ),
    ).toBe("/reports");
    expect(takePendingAppLink()?.target.href).toBe("/reports");
  });

  it("leaves unrelated paths alone", () => {
    expect(rewriteSystemPath("/auth/welcome")).toBe("/auth/welcome");
  });

  it("serializes param hrefs for account detail", () => {
    const target = resolveAppLink(
      "https://beancount.io/ledger/open_ledger/example/account/Assets:Cash",
      { serverUrl: "https://beancount.io" },
    );
    expect(target === null).toBe(false);
    expect(hrefToPath(target!.href)).toBe(
      "/account-detail?account=Assets%3ACash&ledger=open_ledger%2Fexample",
    );
  });
});

// w21/346: the AASA claims /ledger/*, so profile links reached the app and
// were rewritten to Home; Android's /ledger prefix also claimed the ledger
// list, the gallery and the assets.
describe("browserFallbackUrl", () => {
  it("names the browser URL for a ledger link the app has no screen for", () => {
    for (const path of [
      "https://beancount.io/ledger/open_ledger",
      "/ledger/open_ledger",
      "beancount:///ledger/open_ledger",
    ]) {
      expect(browserFallbackUrl(path)).toBe(
        "https://beancount.io/ledger/open_ledger",
      );
    }
  });

  it("leaves mapped links, other paths and foreign hosts alone", () => {
    expect(
      browserFallbackUrl("/ledger/open_ledger/example/balance-sheet"),
    ).toBe(null);
    expect(browserFallbackUrl("/ledger/alice/books")).toBe(null);
    expect(browserFallbackUrl("/auth/welcome")).toBe(null);
    expect(browserFallbackUrl("https://evil.example/ledger/x")).toBe(null);
  });

  it("is what the native intent opens, and Android claims only owner/name paths", () => {
    const intent = fs
      .readFileSync(
        path.join(__dirname, "../../../../app/+native-intent.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(
      intent.includes(
        "constbrowserUrl=browserFallbackUrl(path);if(browserUrl){voidLinking.openURL(browserUrl).catch(()=>undefined);returnnull;}",
      ),
    ).toBe(true);
    const config = JSON.parse(
      fs.readFileSync(path.join(__dirname, "../../../../app.json"), "utf8"),
    );
    const data = config.expo.android.intentFilters[0].data[0];
    expect(data.pathPattern).toBe("/ledger/..*/..*");
    expect(data.pathPrefix).toBe(undefined);
  });
});

// w21/347: the branch segment was dropped, so a link naming another branch
// opened main's file, editable.
describe("a file link on a branch other than main", () => {
  const base = "https://beancount.io/ledger/alice/books/files/blob";

  it("is no app link and goes to the browser", () => {
    expect(resolveAppLink(`${base}/feature-x/main.bean`)).toBe(null);
    expect(browserFallbackUrl(`${base}/feature-x/main.bean`)).toBe(
      `${base}/feature-x/main.bean`,
    );
  });

  it("still opens main's file in the editor", () => {
    expect(resolveAppLink(`${base}/main/accounts/bank.bean`)?.href).toEqual({
      pathname: "/ledger-file-editor",
      params: { path: "accounts/bank.bean", ledger: "alice/books" },
    });
  });
});
