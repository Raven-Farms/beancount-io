import fs from "fs";
import path from "path";
import ts from "typescript";

// Recent Changes and commit detail rendered `commit.message` verbatim, so a
// trailing newline became a blank row line and the empty-diff panel, inside
// the horizontal diff scroller, shrank to its text (w0/032). The splitting
// itself is tested in split-commit-message.test.ts; this guards the wiring.
const parse = (relative: string) => {
  const file = path.join(__dirname, "..", relative);
  return ts.createSourceFile(
    file,
    fs.readFileSync(file, "utf8"),
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
};
const screens = {
  notifications: parse("screens/notifications-screen/notifications-screen.tsx"),
  detail: parse("screens/commit-detail-screen/commit-detail-screen.tsx"),
};

function collect(node: ts.Node, match: (node: ts.Node) => boolean): ts.Node[] {
  const found: ts.Node[] = [];
  (function visit(child: ts.Node) {
    if (match(child)) found.push(child);
    ts.forEachChild(child, visit);
  })(node);
  return found;
}

const renders = (source: ts.SourceFile, expression: string) =>
  collect(
    source,
    (node) =>
      ts.isJsxExpression(node) && node.expression?.getText() === expression,
  ).length;

describe("commit message display", () => {
  it("never renders a raw commit message", () => {
    for (const source of Object.values(screens)) {
      expect(renders(source, "commit.message")).toBe(0);
    }
  });

  it("shows the subject in Recent Changes, for sight and VoiceOver", () => {
    expect(renders(screens.notifications, "commit.subject")).toBe(2);
  });

  it("shows the subject and the reflowed body in commit detail", () => {
    expect(renders(screens.detail, "message.subject")).toBe(1);
    expect(renders(screens.detail, "message.body")).toBe(1);
  });

  it("keeps the empty-diff text outside the horizontal diff scroller", () => {
    const horizontal = collect(
      screens.detail,
      (node) =>
        ts.isJsxElement(node) &&
        node.openingElement.tagName.getText() === "ScrollView" &&
        node.openingElement.attributes.properties.some(
          (attr) =>
            ts.isJsxAttribute(attr) && attr.name.getText() === "horizontal",
        ),
    );
    expect(horizontal.length).toBe(1);
    expect(horizontal[0].getText().includes("commitDetailNoDiff")).toBe(false);
    expect(horizontal[0].getText().includes("DiffLineView")).toBe(true);
  });
});
