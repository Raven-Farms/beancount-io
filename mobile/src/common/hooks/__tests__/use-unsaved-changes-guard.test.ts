import fs from "fs";
import path from "path";
import vm from "vm";
import ts from "typescript";

/**
 * w21/150: the unsaved-changes guards listened for `beforeRemove`, which the
 * native stack does not consult for iOS's swipe-back, so the screen slid away
 * before the alert appeared. Runs the real hook with its dependencies stubbed.
 */
let prevented: boolean | null = null;
let onPrevent: ((options: { data: { action: unknown } }) => void) | null = null;
const dispatched: unknown[] = [];
const alerts: { title: string; buttons: any[] }[] = [];

const hookExports: Record<string, any> = {};
vm.runInNewContext(
  ts.transpileModule(
    fs.readFileSync(
      path.join(__dirname, "..", "use-unsaved-changes-guard.ts"),
      "utf8",
    ),
    { compilerOptions: { module: ts.ModuleKind.CommonJS } },
  ).outputText,
  {
    exports: hookExports,
    require: (id: string) => {
      const modules: Record<string, unknown> = {
        "react-native": {
          Alert: {
            alert: (title: string, _message: string, buttons: any[]) =>
              alerts.push({ title, buttons }),
          },
        },
        "expo-router": {
          useNavigation: () => ({
            dispatch: (action: unknown) => dispatched.push(action),
          }),
        },
        "expo-router/react-navigation": {
          usePreventRemove: (prevent: boolean, callback: typeof onPrevent) => {
            prevented = prevent;
            onPrevent = callback;
          },
        },
        "@/common/hooks/use-translations": {
          useTranslations: () => ({ t: (key: string) => key }),
        },
      };
      if (!(id in modules)) throw new Error(`Unexpected dependency ${id}`);
      return modules[id];
    },
  },
);
const { useUnsavedChangesGuard } = hookExports;

const action = { type: "GO_BACK" };

beforeEach(() => {
  prevented = null;
  onPrevent = null;
  dispatched.length = 0;
  alerts.length = 0;
});

describe("useUnsavedChangesGuard", () => {
  it("prevents removal, swipe-back included, only while there are edits", () => {
    useUnsavedChangesGuard(true);
    expect(prevented).toBe(true);
    useUnsavedChangesGuard(false);
    expect(prevented).toBe(false);
  });

  it("asks first: Cancel stays, Discard leaves", () => {
    useUnsavedChangesGuard(true);
    onPrevent!({ data: { action } });
    expect(alerts.map((alert) => alert.title)).toEqual([
      "ledgerEditorUnsavedTitle",
    ]);
    expect(dispatched).toEqual([]);
    const [cancel, discard] = alerts[0].buttons;
    expect(cancel.style).toBe("cancel");
    discard.onPress();
    expect(dispatched).toEqual([action]);
  });

  it("lets a screen leaving after a save go without asking", () => {
    useUnsavedChangesGuard(true, { current: true });
    onPrevent!({ data: { action } });
    expect(alerts).toEqual([]);
    expect(dispatched).toEqual([action]);
  });

  it("is what every guarded screen uses, with no beforeRemove listener left", () => {
    const screens = path.join(__dirname, "..", "..", "..", "screens");
    for (const [file, call] of [
      [
        "ledger-file-editor-screen/index.tsx",
        "useUnsavedChangesGuard(hasUnsavedChanges);",
      ],
      [
        "edit-transaction-screen/edit-transaction-screen.tsx",
        "useUnsavedChangesGuard(hasUnsavedChanges, savedOutRef);",
      ],
      [
        "multi-postings-transaction/multi-postings-transaction-screen.tsx",
        "useUnsavedChangesGuard(hasUnsavedChanges, savedOutRef);",
      ],
    ]) {
      const source = fs.readFileSync(path.join(screens, file), "utf8");
      expect(source.includes(call)).toBe(true);
      expect(source.includes('addListener("beforeRemove"')).toBe(false);
    }
  });
});
