import fs from "fs";
import path from "path";
import ts from "typescript";

describe("header action font scaling coverage", () => {
  it("applies headerActionMaxFontSizeMultiplier on Edit Transaction actions", () => {
    const source = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "screens",
        "edit-transaction-screen",
        "edit-transaction-screen.tsx",
      ),
      "utf8",
    );
    expect(source.includes("headerActionMaxFontSizeMultiplier")).toBe(true);
    const matches =
      source.match(
        /maxFontSizeMultiplier=\{headerActionMaxFontSizeMultiplier\}/g,
      ) ?? [];
    expect(matches.length >= 2).toBe(true);
  });

  it("applies the same cap on Create Ledger and File Editor Save", () => {
    const createLedger = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "screens",
        "create-ledger-screen",
        "create-ledger-screen.tsx",
      ),
      "utf8",
    );
    const fileEditor = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "screens",
        "ledger-file-editor-screen",
        "index.tsx",
      ),
      "utf8",
    );
    expect(createLedger.includes("headerActionMaxFontSizeMultiplier")).toBe(
      true,
    );
    expect(fileEditor.includes("headerActionMaxFontSizeMultiplier")).toBe(true);
  });
});

// Add Budget's header Done grew past every other form's action and its own
// title at accessibility sizes: the cap was applied screen by screen and that
// one was missed (w0/040). Every text a header renders on the right must carry
// the shared cap, so the next new form cannot skip it.
describe("every headerRight text action", () => {
  const sourceRoot = path.join(__dirname, "..");
  const files: string[] = [];
  (function walk(dir: string) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (!["__tests__", "generated-graphql"].includes(entry.name))
          walk(full);
      } else if (entry.name.endsWith(".tsx")) {
        files.push(full);
      }
    }
  })(sourceRoot);

  type HeaderText = { file: string; capped: boolean };
  const headerTexts: HeaderText[] = [];
  for (const file of files) {
    const source = ts.createSourceFile(
      file,
      fs.readFileSync(file, "utf8"),
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    (function visit(node: ts.Node) {
      if (
        ts.isPropertyAssignment(node) &&
        node.name.getText() === "headerRight"
      ) {
        (function texts(child: ts.Node) {
          const opening = ts.isJsxElement(child)
            ? child.openingElement
            : ts.isJsxSelfClosingElement(child)
              ? child
              : null;
          if (opening && opening.tagName.getText() === "Text") {
            headerTexts.push({
              file: path.relative(sourceRoot, file),
              capped: opening.attributes.properties.some(
                (attr) =>
                  ts.isJsxAttribute(attr) &&
                  attr.name.getText() === "maxFontSizeMultiplier" &&
                  attr.initializer?.getText() ===
                    "{headerActionMaxFontSizeMultiplier}",
              ),
            });
          }
          ts.forEachChild(child, texts);
        })(node.initializer);
      }
      ts.forEachChild(node, visit);
    })(source);
  }

  it("finds the form headers it guards", () => {
    const covered = new Set(headerTexts.map((text) => text.file));
    expect(covered.size >= 7).toBe(true);
    expect(covered.has("screens/add-budget-screen/add-budget-screen.tsx")).toBe(
      true,
    );
  });

  it("caps each one at headerActionMaxFontSizeMultiplier", () => {
    expect(
      headerTexts.filter((text) => !text.capped).map((text) => text.file),
    ).toEqual([]);
  });
});
