import fs from "fs";
import path from "path";
import { detectIndentUnit, wrapSelection } from "../indent-unit";

// w21/339: Enter turned a Makefile's tab indentation into spaces ("missing
// separator"), no key typed a tab, and `""` replaced a selection.
describe("detectIndentUnit", () => {
  it("indents a tab-indented file with a tab", () => {
    expect(detectIndentUnit("all:\n\tbean-check main.bean")).toBe("\t");
    expect(detectIndentUnit("def f():\n\treturn 1\n\nclass A:\n\tpass")).toBe(
      "\t",
    );
  });

  it("keeps two spaces for a space-indented or unindented file", () => {
    expect(
      detectIndentUnit('2026-10-20 * "Coffee"\n  Expenses:Food 4 USD'),
    ).toBe("  ");
    expect(detectIndentUnit("")).toBe("  ");
    expect(detectIndentUnit("no indentation at all")).toBe("  ");
  });

  it("follows whichever the document mostly uses", () => {
    expect(detectIndentUnit("a:\n\tb\n\tc\n  d")).toBe("\t");
    expect(detectIndentUnit("a:\n\tb\n  c\n  d")).toBe("  ");
  });

  it("does not count a whitespace-only line", () => {
    expect(detectIndentUnit("a:\n\tb\n   \n   ")).toBe("\t");
  });
});

describe("wrapSelection", () => {
  it("wraps a selection in the pair", () => {
    expect(wrapSelection('""', 1, "hello world")).toEqual({
      text: '"hello world"',
      selectFrom: 1,
      selectTo: 12,
    });
  });

  it("does nothing for an empty selection or a button that is not a pair", () => {
    expect(wrapSelection('""', 1, "")).toBe(null);
    expect(wrapSelection("* ", undefined, "x")).toBe(null);
    expect(wrapSelection("2026-10-21 ", undefined, "x")).toBe(null);
  });
});

describe("the editor", () => {
  const editor = fs
    .readFileSync(path.join(__dirname, "..", "code-editor.tsx"), "utf8")
    .replace(/\s+/gu, "");

  it("indents with the document's unit and binds Tab", () => {
    expect(
      editor.includes(
        'indentUnit.compute(["doc"],(state)=>detectIndentUnit(state.doc.toString()),',
      ),
    ).toBe(true);
    expect(editor.includes("keymap.of([indentWithTab,...defaultKeymap,")).toBe(
      true,
    );
  });

  it("turns the ⇥ token into the unit and wraps a selection for a pair", () => {
    expect(
      editor.includes(
        "insertSpec.text===INSERT_INDENT?view.state.facet(indentUnit):insertSpec.text",
      ),
    ).toBe(true);
    expect(editor.includes("wrapSelection(text,insertSpec.cursorOffset,")).toBe(
      true,
    );
  });
});
