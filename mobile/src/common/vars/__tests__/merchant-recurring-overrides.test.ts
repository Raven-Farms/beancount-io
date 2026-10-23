import fs from "fs";
import path from "path";
import vm from "vm";
import ts from "typescript";
import * as merchantKeyModule from "../../merchant-key";

/**
 * w21/169: manual Recurring marks were keyed by the displayed spelling, so
 * one was lost when another spelling took the majority. Runs the real module
 * with its persistent var stubbed.
 */
let state: Record<string, Record<string, string>> = {};
const moduleExports: Record<string, any> = {};
vm.runInNewContext(
  ts.transpileModule(
    fs.readFileSync(
      path.join(__dirname, "..", "merchant-recurring-overrides.ts"),
      "utf8",
    ),
    { compilerOptions: { module: ts.ModuleKind.CommonJS } },
  ).outputText,
  {
    exports: moduleExports,
    require: (id: string) => {
      if (id === "@/common/merchant-key") return merchantKeyModule;
      if (id === "@/common/apollo/persistent-var")
        return {
          createPersistentVar: () => [
            (next?: typeof state) => {
              if (next !== undefined) state = next;
              return state;
            },
            async () => undefined,
            async () => undefined,
          ],
        };
      throw new Error(`Unexpected dependency ${id}`);
    },
  },
);
const { overrideFor, toggleRecurringOverride } = moduleExports;

beforeEach(() => {
  state = {};
});

describe("merchant recurring overrides", () => {
  it("survive the display spelling flipping", () => {
    toggleRecurringOverride("alice/books", "QaFlix", false, false);
    expect(overrideFor(state, "alice/books", "QAFLIX")).toBe("recurring");
    expect(JSON.stringify(state)).toBe(
      JSON.stringify({ "alice/books": { qaflix: "recurring" } }),
    );
  });

  it("read a mark saved under a spelling before marks were keyed", () => {
    state = { "alice/books": { QaFlix: "notRecurring" } };
    expect(overrideFor(state, "alice/books", "QAFLIX")).toBe("notRecurring");
  });

  it("replace an old spelling's mark instead of keeping two", () => {
    state = { "alice/books": { QaFlix: "notRecurring" } };
    toggleRecurringOverride("alice/books", "QAFLIX", false, false);
    expect(JSON.stringify(state)).toBe(
      JSON.stringify({ "alice/books": { qaflix: "recurring" } }),
    );
  });

  it("clear a mark saved under an old spelling", () => {
    state = { "alice/books": { QaFlix: "recurring" } };
    toggleRecurringOverride("alice/books", "QAFLIX", true, false);
    expect(JSON.stringify(state)).toBe("{}");
  });
});
