import fs from "fs";
import path from "path";
import ts from "typescript";

/**
 * With camera access denied, Scan Receipt offered only Cancel and Open
 * Settings, so a receipt already in the photo library could not be scanned
 * (w21/017). The denied state now leads with Choose from Library, wired to the
 * same picker the camera's top bar uses. Checked on the source: the screen
 * needs expo-camera, which the unit runner cannot load.
 */
const file = path.join(__dirname, "..", "camera-view.tsx");
const source = ts.createSourceFile(
  file,
  fs.readFileSync(file, "utf8"),
  ts.ScriptTarget.Latest,
  true,
  ts.ScriptKind.TSX,
);

/** The JSX returned under `if (!permission.granted)`. */
function deniedBranch(): ts.Node {
  let branch: ts.Node | undefined;
  const visit = (node: ts.Node) => {
    if (
      ts.isIfStatement(node) &&
      node.expression.getText() === "!permission.granted"
    ) {
      branch = node.thenStatement;
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  if (!branch) throw new Error("denied-camera branch not found");
  return branch;
}

function pressables(root: ts.Node) {
  const found: ts.JsxOpeningElement[] = [];
  const visit = (node: ts.Node) => {
    if (
      ts.isJsxOpeningElement(node) &&
      node.tagName.getText() === "Pressable"
    ) {
      found.push(node);
    }
    ts.forEachChild(node, visit);
  };
  visit(root);
  const attr = (element: ts.JsxOpeningElement, name: string) =>
    element.attributes.properties
      .filter(ts.isJsxAttribute)
      .find((a) => a.name.getText() === name)
      ?.initializer?.getText();
  return found.map((element) => ({
    onPress: attr(element, "onPress") ?? "",
    role: attr(element, "accessibilityRole"),
    label: (element.parent as ts.JsxElement).children
      .map((child) => child.getText())
      .join(""),
  }));
}

describe("Scan Receipt with camera access denied", () => {
  const actions = pressables(deniedBranch());

  it("offers Choose from Library first, wired to the library picker", () => {
    expect(actions[0]?.onPress).toBe("{onPickFromLibrary}");
    expect(actions[0]?.label.includes('t("receiptChooseLibrary")')).toBe(true);
  });

  it("keeps Cancel and Open Settings, every action a button", () => {
    expect(actions.length).toBe(3);
    expect(actions[1]?.label.includes('t("receiptCancel")')).toBe(true);
    expect(actions[2]?.label.includes('t("receiptOpenSettings")')).toBe(true);
    for (const action of actions) expect(action.role).toBe('"button"');
  });
});
