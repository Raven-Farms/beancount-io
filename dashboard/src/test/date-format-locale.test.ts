import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "fs";
import { join, relative } from "path";
import ts from "typescript";

/**
 * Static guard: a date-fns `format` pattern that prints month or weekday
 * names, or a localized format (`P…`), must pass the reader's `locale`.
 * Without one, date-fns writes English — "Verknüpft am Feb 13, 2026" on the
 * German Plaid card (w0/048). Numeric patterns (`yyyy-MM-dd`) are exempt.
 */

const SRC_ROOT = join(__dirname, "..");

/** Month names (MMM, LLL…), weekdays (E, eee, ccc…) and localized `P` formats. */
const NAMED_TOKENS = /M{3,}|L{3,}|E+|e{3,}|c{3,}|P+/;

/** A pattern's tokens, with its 'quoted literal' text removed. */
function printsNames(pattern: string): boolean {
  return NAMED_TOKENS.test(pattern.replace(/'[^']*'/g, ""));
}

/** `format(…)` calls from date-fns in `source` that name things without a locale. */
function unlocalizedNamedFormats(source: string): string[] {
  const file = ts.createSourceFile(
    "file.tsx",
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
  const formatNames = new Set<string>();
  for (const statement of file.statements) {
    if (
      ts.isImportDeclaration(statement) &&
      ts.isStringLiteral(statement.moduleSpecifier) &&
      statement.moduleSpecifier.text === "date-fns" &&
      statement.importClause?.namedBindings &&
      ts.isNamedImports(statement.importClause.namedBindings)
    ) {
      for (const element of statement.importClause.namedBindings.elements) {
        if ((element.propertyName ?? element.name).text === "format") {
          formatNames.add(element.name.text);
        }
      }
    }
  }
  const offenders: string[] = [];
  const visit = (node: ts.Node) => {
    if (
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      formatNames.has(node.expression.text)
    ) {
      const [, pattern, options] = node.arguments;
      const hasLocale =
        options !== undefined &&
        ts.isObjectLiteralExpression(options) &&
        options.properties.some(
          (property) =>
            (ts.isPropertyAssignment(property) ||
              ts.isShorthandPropertyAssignment(property)) &&
            property.name.getText(file) === "locale",
        );
      if (
        pattern &&
        ts.isStringLiteralLike(pattern) &&
        printsNames(pattern.text) &&
        !hasLocale
      ) {
        offenders.push(node.getText(file));
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return offenders;
}

function productionSources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) {
      return name === "__tests__" || name === "test"
        ? []
        : productionSources(path);
    }
    return /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) ? [path] : [];
  });
}

describe("date-fns names are localized", () => {
  it("passes the reader's locale wherever a pattern prints names", () => {
    const offenders = productionSources(SRC_ROOT).flatMap((path) =>
      unlocalizedNamedFormats(readFileSync(path, "utf8")).map(
        (call) => `${relative(SRC_ROOT, path)}: ${call}`,
      ),
    );
    expect(offenders).toEqual([]);
  });

  it("flags a month name without a locale and nothing else", () => {
    const source = (call: string) =>
      `import { format as fmt } from "date-fns";\nconst x = ${call};`;
    expect(unlocalizedNamedFormats(source('fmt(d, "MMM d, yyyy")'))).toEqual([
      'fmt(d, "MMM d, yyyy")',
    ]);
    expect(unlocalizedNamedFormats(source('fmt(d, "PP")'))).toHaveLength(1);
    expect(unlocalizedNamedFormats(source('fmt(d, "EEEE")'))).toHaveLength(1);
    expect(unlocalizedNamedFormats(source('fmt(d, "PP", { locale })'))).toEqual(
      [],
    );
    expect(unlocalizedNamedFormats(source('fmt(d, "yyyy-MM-dd")'))).toEqual([]);
    // Quoted literal text is not a token.
    expect(unlocalizedNamedFormats(source("fmt(d, \"yyyy 'Mon'\")"))).toEqual(
      [],
    );
  });
});
