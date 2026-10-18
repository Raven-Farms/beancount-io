import fs from "fs";
import path from "path";
import ts from "typescript";

// Under Persian (right-to-left), inputs styled with LEADING_TEXT_ALIGN — or
// with no alignment — stayed on the physical left while their labels
// mirrored: an iOS TextInput gets no left/right swap (w0/045). Inputs that
// start at the leading edge use leadingInputTextAlign(); LEADING_TEXT_ALIGN is
// for Text only. The direction branch itself is tested in rtl.test.ts.
const sourceRoot = path.join(__dirname, "..");

function tsxFiles(dir: string, out: string[] = []): string[] {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!["__tests__", "generated-graphql"].includes(entry.name)) {
        tsxFiles(full, out);
      }
    } else if (entry.name.endsWith(".tsx")) {
      out.push(full);
    }
  }
  return out;
}

type Input = {
  file: string;
  tag: "TextInput" | "Text";
  styleKeys: string[];
  textAlign: string[];
};

/** Every TextInput, with the `styles.<key>` it uses and each key's textAlign. */
function inputs(): Input[] {
  const found: Input[] = [];
  for (const file of tsxFiles(sourceRoot)) {
    const source = ts.createSourceFile(
      file,
      fs.readFileSync(file, "utf8"),
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    const alignByKey = new Map<string, string>();
    const styleRefs: { tag: "TextInput" | "Text"; keys: string[] }[] = [];
    (function visit(node: ts.Node) {
      if (
        ts.isPropertyAssignment(node) &&
        node.name.getText() === "textAlign" &&
        ts.isObjectLiteralExpression(node.parent) &&
        ts.isPropertyAssignment(node.parent.parent)
      ) {
        alignByKey.set(
          node.parent.parent.name.getText(),
          node.initializer.getText(),
        );
      }
      const opening = ts.isJsxElement(node)
        ? node.openingElement
        : ts.isJsxSelfClosingElement(node)
          ? node
          : null;
      const tag = opening?.tagName.getText();
      if (opening && (tag === "TextInput" || tag === "Text")) {
        const style = opening.attributes.properties.find(
          (attr) => ts.isJsxAttribute(attr) && attr.name.getText() === "style",
        );
        const text = style && ts.isJsxAttribute(style) ? style.getText() : "";
        styleRefs.push({
          tag,
          keys: [...text.matchAll(/styles\.(\w+)/g)].map((match) => match[1]!),
        });
      }
      ts.forEachChild(node, visit);
    })(source);
    for (const { tag, keys } of styleRefs) {
      found.push({
        file: path.relative(sourceRoot, file),
        tag,
        styleKeys: keys,
        textAlign: keys
          .map((key) => alignByKey.get(key))
          .filter((align): align is string => align !== undefined),
      });
    }
  }
  return found;
}

describe("text input alignment under right-to-left", () => {
  const found = inputs();
  const all = found.filter((input) => input.tag === "TextInput");

  it("never aligns a TextInput with LEADING_TEXT_ALIGN", () => {
    expect(
      all
        .filter((input) => input.textAlign.includes("LEADING_TEXT_ALIGN"))
        .map((input) => input.file),
    ).toEqual([]);
  });

  it("starts the leading-edge inputs at the leading edge in both directions", () => {
    const leading = new Set(
      all
        .filter((input) => input.textAlign.includes("leadingInputTextAlign()"))
        .map((input) => input.file),
    );
    for (const file of [
      "screens/profile/profile-screen.tsx",
      "components/text-input-screen/index.tsx",
      "screens/create-ledger-screen/create-ledger-screen.tsx",
      "screens/ledger-selection/index.tsx",
      "screens/agent-screen/agent-screen.tsx",
    ]) {
      expect(leading.has(file)).toBe(true);
    }
  });

  it("never leaves a Text on an input's alignment", () => {
    // iOS flips a Text's "right" under right-to-left, so the input value
    // lands a Text on the trailing edge: Profile's read-only email did.
    const last = (aligns: string[]) => aligns[aligns.length - 1];
    expect(
      found
        .filter(
          (text) =>
            text.tag === "Text" &&
            last(text.textAlign) === "leadingInputTextAlign()",
        )
        .map((text) => `${text.file} ${text.styleKeys.join("+")}`),
    ).toEqual([]);
  });
});
