import fs from "fs";
import path from "path";
import ts from "typescript";

/**
 * Keying a Text on `fontScale` remounts it on a live text-size change. Two
 * siblings keyed on the same expression share a key, which React rejects:
 * Transaction Filters logged "two children with the same key, `1`" as soon as
 * its range error appeared beside the section title (w21/026). Every scale key
 * among one parent's children must differ.
 */
function tsxFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      return entry.name === "__tests__" || entry.name === "generated-graphql"
        ? []
        : tsxFiles(full);
    }
    return entry.name.endsWith(".tsx") ? [full] : [];
  });
}

/** JSX elements a parent renders directly, looking through `{cond ? … : …}`. */
function childElements(node: ts.Node): ts.JsxOpeningLikeElement[] {
  if (ts.isJsxElement(node)) return [node.openingElement];
  if (ts.isJsxSelfClosingElement(node)) return [node];
  if (ts.isJsxFragment(node)) return node.children.flatMap(childElements);
  const found: ts.JsxOpeningLikeElement[] = [];
  ts.forEachChild(node, (child) => {
    found.push(...childElements(child));
  });
  return found;
}

const keyOf = (element: ts.JsxOpeningLikeElement) =>
  element.attributes.properties
    .filter(ts.isJsxAttribute)
    .find((attr) => attr.name.getText() === "key")
    ?.initializer?.getText();

describe("fontScale keys", () => {
  it("never repeat among one parent's children", () => {
    const collisions: string[] = [];
    for (const file of tsxFiles(path.join(__dirname, ".."))) {
      const source = ts.createSourceFile(
        file,
        fs.readFileSync(file, "utf8"),
        ts.ScriptTarget.Latest,
        true,
        ts.ScriptKind.TSX,
      );
      const visit = (node: ts.Node) => {
        if (ts.isJsxElement(node)) {
          const keys = node.children
            .flatMap(childElements)
            .map(keyOf)
            .filter((key): key is string =>
              Boolean(key?.includes("fontScale")),
            );
          const repeated = keys.filter((key, i) => keys.indexOf(key) !== i);
          for (const key of new Set(repeated)) {
            collisions.push(
              `${path.relative(path.join(__dirname, ".."), file)}:${
                source.getLineAndCharacterOfPosition(node.getStart()).line + 1
              } ${key}`,
            );
          }
        }
        ts.forEachChild(node, visit);
      };
      visit(source);
    }
    expect(collisions).toEqual([]);
  });
});
