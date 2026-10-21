import fs from "fs";
import path from "path";
import vm from "vm";
import ts from "typescript";
import * as guard from "../../unsaved-edits-guard";

/**
 * w21/090: an app link to another ledger switched `ledgerVar` before it
 * navigated, which remounted the file editor clean and threw its draft away
 * without the unsaved-changes alert. Runs the real `openAppLinkTarget`.
 */
let ledger: string | null = "alice/books";
const replaced: string[] = [];
function load() {
  const exports: Record<string, any> = {};
  const source = ts.transpileModule(
    fs.readFileSync(path.join(__dirname, "..", "open-app-link.ts"), "utf8"),
    { compilerOptions: { module: ts.ModuleKind.CommonJS } },
  ).outputText;
  const modules: Record<string, unknown> = {
    "@apollo/client": {},
    "expo-router": {
      router: { replace: (href: string) => replaced.push(href) },
    },
    "react-native": {
      InteractionManager: { runAfterInteractions: (fn: () => void) => fn() },
      Linking: { openURL: async () => {} },
    },
    "@/generated-graphql/graphql": { GetLedgerDocument: "GetLedger" },
    "@/common/vars": {
      ledgerVar: (next?: string) => {
        if (next !== undefined) ledger = next;
        return ledger;
      },
    },
    "@/common/unsaved-edits-guard": guard,
    "./oauth-callback-url": { isOAuthCallbackUrl: () => false },
  };
  vm.runInNewContext(source, {
    exports,
    setTimeout,
    require: (id: string) => {
      if (!(id in modules)) throw new Error(`Unexpected dependency ${id}`);
      return modules[id];
    },
  });
  return exports;
}

const { openAppLinkTarget } = load();
const client = { query: async () => ({ data: {} }) };
// Results come from the vm's realm, so compare them as JSON.
const open = async (ledgerFullName: string) =>
  JSON.stringify(
    await openAppLinkTarget({
      client,
      target: { ledgerFullName, href: "/transactions" },
      sourceUrl: `https://beancount.io/ledger/${ledgerFullName}/journal`,
      isCurrentSession: () => true,
    }),
  );

describe("an app link to another ledger with a dirty editor", () => {
  let unregister: () => void = () => {};
  let asked = 0;
  let answer = false;

  beforeEach(() => {
    ledger = "alice/books";
    replaced.length = 0;
    asked = 0;
    unregister = guard.registerUnsavedEditsGuard(async () => {
      asked += 1;
      return answer;
    });
  });
  afterEach(() => unregister());

  it("keeps the editor, its draft and the ledger on Cancel", async () => {
    answer = false;
    expect(await open("bob/other")).toBe(
      JSON.stringify({ ok: false, reason: "aborted" }),
    );
    expect(asked).toBe(1);
    expect(ledger).toBe("alice/books");
    expect(replaced).toEqual([]);
  });

  it("switches the ledger and navigates on Discard", async () => {
    answer = true;
    expect(await open("bob/other")).toBe(JSON.stringify({ ok: true }));
    expect(ledger).toBe("bob/other");
    expect(replaced).toEqual(["/transactions"]);
  });

  it("leaves a same-ledger link to the editor's own guard", async () => {
    expect(await open("alice/books")).toBe(JSON.stringify({ ok: true }));
    expect(asked).toBe(0);
  });

  it("follows the link directly once the editor is clean", async () => {
    unregister();
    expect(await open("bob/other")).toBe(JSON.stringify({ ok: true }));
    expect(asked).toBe(0);
  });

  it("is registered by the editor while it has unsaved changes", () => {
    const editor = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "..",
        "..",
        "screens",
        "ledger-file-editor-screen",
        "index.tsx",
      ),
      "utf8",
    );
    expect(editor.includes("return registerUnsavedEditsGuard(")).toBe(true);
    expect(editor.includes("if (!hasUnsavedChanges) return undefined;")).toBe(
      true,
    );
  });
});

// w21/131: the owner in a link is matched case-insensitively, but the typed
// spelling was selected, so the app read its own ledger as read-only.
describe("an app link with a differently-cased owner", () => {
  const canonicalClient = {
    query: async () => ({ data: { getLedger: { id: "alice.smith/books" } } }),
  };
  const openAs = async (target: { ledgerFullName: string; href: unknown }) =>
    JSON.stringify(
      await openAppLinkTarget({
        client: canonicalClient,
        target,
        sourceUrl: "https://beancount.io/ledger/Alice.Smith/books",
        isCurrentSession: () => true,
      }),
    );

  beforeEach(() => {
    ledger = "alice.smith/books";
    replaced.length = 0;
  });

  it("selects the ledger id the server returned", async () => {
    expect(
      await openAs({ ledgerFullName: "Alice.Smith/books", href: "/" }),
    ).toBe(JSON.stringify({ ok: true }));
    expect(ledger).toBe("alice.smith/books");
  });

  it("binds a detail screen to that id too", async () => {
    await openAs({
      ledgerFullName: "Alice.Smith/books",
      href: {
        pathname: "/account-detail",
        params: { account: "Assets:Cash", ledger: "Alice.Smith/books" },
      },
    });
    expect(JSON.stringify(replaced)).toBe(
      JSON.stringify([
        {
          pathname: "/account-detail",
          params: { account: "Assets:Cash", ledger: "alice.smith/books" },
        },
      ]),
    );
  });
});
