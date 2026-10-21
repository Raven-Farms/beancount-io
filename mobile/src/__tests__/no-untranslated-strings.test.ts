import fs from "fs";
import path from "path";
import ts from "typescript";

/**
 * Static guard: user-facing English written into the code instead of the
 * translation files. The locale tests check only those files, and English
 * leaked past them in the shapes below (w21/178): a literal
 * `accessibilityLabel`, a `?? "Pending"` fallback in a helper (w21/140), a
 * default prop ("Done"), a fixed `placeholder="YYYY-MM-DD"`.
 *
 * Scans `src/` and `app/` with the TypeScript parser. Copy-like means a word
 * of two letters or more; for fallbacks, defaults and call arguments it must
 * also look like a sentence (a capital first letter, or a space), so type
 * tags such as `"success"` pass.
 */
const PKG = path.join(__dirname, "..", "..");
const ROOTS = ["src", "app"].map((dir) => path.join(PKG, dir));
const SKIP = /__tests__|[\\/]translations[\\/]|generated-graphql|\.d\.ts$/;

/** JSX attributes that are read or shown to the user. */
const COPY_ATTRIBUTES = new Set([
  "accessibilityLabel",
  "accessibilityHint",
  "placeholder",
  "title",
  "headerTitle",
  "label",
  "message",
]);
/** Object keys that carry copy: `Stack.Screen` options, `accessibilityValue`, toasts. */
const COPY_KEYS = new Set([
  "title",
  "headerTitle",
  "headerBackTitle",
  "text",
  "message",
  "label",
  "placeholder",
]);

/**
 * Literals that are not copy: the brand, URLs, and Beancount's default root
 * names, which are ledger data a renamed root replaces.
 */
const ALLOWED = new Set([
  "Beancount.io",
  "Assets",
  "Liabilities",
  "Equity",
  "Income",
  "Expenses",
]);

const hasWord = (text: string) => /[A-Za-z]{2,}/.test(text);
const sentenceLike = (text: string) =>
  hasWord(text) && /^[A-Z][a-z]|\s/.test(text.trim());
const allowed = (text: string) =>
  ALLOWED.has(text.trim()) || /^https?:\/\//.test(text.trim());

/** Every untranslated string in `source`, as "line: text". */
function leaks(source: string, fileName = "file.tsx"): string[] {
  const file = ts.createSourceFile(
    fileName,
    source,
    ts.ScriptTarget.Latest,
    true,
    fileName.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
  const found: string[] = [];
  const report = (node: ts.Node, text: string) => {
    if (allowed(text)) return;
    const line = file.getLineAndCharacterOfPosition(node.getStart()).line + 1;
    found.push(`${line}: ${JSON.stringify(text)}`);
  };
  const literal = (node: ts.Node | undefined) =>
    node && ts.isStringLiteralLike(node) ? node.text : null;

  const visit = (node: ts.Node) => {
    if (ts.isJsxAttribute(node) && COPY_ATTRIBUTES.has(node.name.getText())) {
      const init = node.initializer;
      const text =
        init && ts.isStringLiteral(init)
          ? init.text
          : init && ts.isJsxExpression(init)
            ? literal(init.expression)
            : null;
      if (text !== null && hasWord(text)) report(node, text);
    } else if (ts.isJsxText(node) && hasWord(node.getText())) {
      report(node, node.getText().trim());
    } else if (
      ts.isBinaryExpression(node) &&
      (node.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken ||
        node.operatorToken.kind === ts.SyntaxKind.BarBarToken)
    ) {
      const text = literal(node.right);
      if (text !== null && sentenceLike(text)) report(node, text);
    } else if (
      (ts.isBindingElement(node) || ts.isParameter(node)) &&
      node.initializer
    ) {
      const text = literal(node.initializer);
      if (text !== null && sentenceLike(text)) report(node, text);
    } else if (
      ts.isCallExpression(node) &&
      /(^|\.)(alert|showToast)$/.test(node.expression.getText())
    ) {
      for (const argument of node.arguments) {
        const text = literal(argument);
        if (text !== null && sentenceLike(text)) report(argument, text);
      }
    } else if (
      ts.isPropertyAssignment(node) &&
      COPY_KEYS.has(node.name.getText())
    ) {
      const text = literal(node.initializer);
      if (text !== null && sentenceLike(text)) report(node, text);
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return found;
}

function sourceFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return SKIP.test(full) ? [] : sourceFiles(full);
    return /\.tsx?$/.test(entry.name) && !SKIP.test(full) ? [full] : [];
  });
}

describe("no untranslated user-facing strings", () => {
  it("finds none in src/ or app/", () => {
    const found = ROOTS.flatMap(sourceFiles).flatMap((file) =>
      leaks(fs.readFileSync(file, "utf8"), file).map(
        (leak) => `${path.relative(PKG, file)}:${leak}`,
      ),
    );
    expect(found).toEqual([]);
  });

  it("catches the shapes that leaked before", () => {
    const sample = `
      function Row({ confirmText = "Done" }) {
        const status = flag ?? "Pending";
        Alert.alert("Could not save");
        return (
          <View accessibilityLabel="Close">
            <TextInput placeholder="YYYY-MM-DD" />
            <Text>Hello there</Text>
          </View>
        );
      }
    `;
    expect(leaks(sample).map((leak) => leak.split(": ")[1])).toEqual([
      '"Done"',
      '"Pending"',
      '"Could not save"',
      '"Close"',
      '"YYYY-MM-DD"',
      '"Hello there"',
    ]);
  });

  it("lets through what is not copy", () => {
    const sample = `
      const kind = result ?? "success";
      const root = name || "Expenses";
      const link = <Text accessibilityLabel={t("close")}>{"·"}</Text>;
      const url = <TextInput placeholder="https://ledger.example.com/" />;
    `;
    expect(leaks(sample)).toEqual([]);
  });
});
