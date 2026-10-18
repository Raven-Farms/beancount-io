import fs from "fs";
import path from "path";
import ts from "typescript";

// The account page decides which way its changes color — salary favorable,
// spending not (w0/033). The rule itself is tested with the row, the chart
// trend and accountCategory; this guards that the screen hands it to both.
const file = path.join(__dirname, "..", "account-detail-screen.tsx");
const source = ts.createSourceFile(
  file,
  fs.readFileSync(file, "utf8"),
  ts.ScriptTarget.Latest,
  true,
  ts.ScriptKind.TSX,
);

function signPassedTo(tag: string): string[] {
  const found: string[] = [];
  (function visit(node: ts.Node) {
    if (
      (ts.isJsxSelfClosingElement(node) || ts.isJsxOpeningElement(node)) &&
      node.tagName.getText() === tag
    ) {
      for (const attr of node.attributes.properties) {
        if (ts.isJsxAttribute(attr) && attr.name.getText() === "netWorthSign") {
          found.push(attr.initializer?.getText() ?? "");
        }
      }
    }
    ts.forEachChild(node, visit);
  })(source);
  return found;
}

describe("account page net-worth sign", () => {
  it("colors journal rows by the account's category", () => {
    expect(signPassedTo("AccountEntryRow")).toEqual(["{netWorthSign}"]);
  });

  it("colors the balance chart by the same category", () => {
    expect(signPassedTo("BalanceChartCard")).toEqual(["{netWorthSign}"]);
  });

  it("derives the sign from the ledger's own root names", () => {
    const text = source.getText();
    expect(text.includes("NET_WORTH_SIGN[category]")).toBe(true);
    expect(text.includes("income: roots?.nameIncome")).toBe(true);
  });
});
