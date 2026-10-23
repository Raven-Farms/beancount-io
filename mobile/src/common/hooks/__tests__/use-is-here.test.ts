import fs from "fs";
import path from "path";
import vm from "vm";
import ts from "typescript";

/**
 * w21/194: a save or delete that finished after the user left still navigated,
 * and expo-router's global `back()`/`dismiss(2)` closed whatever screen was on
 * top. Runs the real hook with React and the navigation stubbed.
 */
let focused = true;
let cleanup: (() => void) | undefined;
const hookExports: Record<string, any> = {};
vm.runInNewContext(
  ts.transpileModule(
    fs.readFileSync(path.join(__dirname, "..", "use-is-here.ts"), "utf8"),
    { compilerOptions: { module: ts.ModuleKind.CommonJS } },
  ).outputText,
  {
    exports: hookExports,
    require: (id: string) => {
      if (id === "react")
        return {
          useRef: (initial: unknown) => ({ current: initial }),
          useEffect: (effect: () => (() => void) | void) => {
            cleanup = effect() ?? undefined;
          },
          useCallback: (fn: unknown) => fn,
        };
      if (id === "expo-router")
        return { useNavigation: () => ({ isFocused: () => focused }) };
      throw new Error(`Unexpected dependency ${id}`);
    },
  },
);
const { useIsHere } = hookExports;

beforeEach(() => {
  focused = true;
  cleanup = undefined;
});

describe("useIsHere", () => {
  it("is true while the screen is focused", () => {
    const isHere = useIsHere();
    expect(isHere()).toBe(true);
  });

  it("is false once another screen is on top", () => {
    const isHere = useIsHere();
    focused = false;
    expect(isHere()).toBe(false);
    focused = true;
    expect(isHere()).toBe(true);
  });

  it("is false once the screen is gone", () => {
    const isHere = useIsHere();
    cleanup?.();
    expect(isHere()).toBe(false);
  });
});

describe("post-write navigation checks it", () => {
  const src = path.join(__dirname, "..", "..", "..");
  const read = (relative: string) =>
    fs.readFileSync(path.join(src, relative), "utf8");

  it("is how the shared write sequence goes back", () => {
    const hook = read("common/hooks/use-ledger-write.ts");
    expect(hook.includes("if (isHere()) router.back();")).toBe(true);
  });

  it("gates each screen's own navigation", () => {
    expect(
      read(
        "screens/multi-postings-transaction/multi-postings-transaction-screen.tsx",
      ).includes("if (!isHere()) return;"),
    ).toBe(true);
    const edit = read(
      "screens/edit-transaction-screen/edit-transaction-screen.tsx",
    );
    expect(edit.includes("const here = isHere();")).toBe(true);
    expect(edit.includes('if (here && exit.kind === "detail")')).toBe(true);
    expect(edit.includes("} else if (here) {")).toBe(true);
    expect(
      read("screens/add-budget-screen/add-budget-screen.tsx").includes(
        "if (!isHere()) {",
      ),
    ).toBe(true);
    expect(
      read("screens/open-account-screen/open-account-screen.tsx").includes(
        "if (isHere()) {",
      ),
    ).toBe(true);
    expect(
      read("screens/profile/profile-screen.tsx").includes(
        "if (!isHere()) return;",
      ),
    ).toBe(true);
  });
});
