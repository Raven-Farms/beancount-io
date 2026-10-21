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
