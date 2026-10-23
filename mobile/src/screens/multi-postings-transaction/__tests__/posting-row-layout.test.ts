import fs from "fs";
import path from "path";
import { prefersStackedLayout } from "../../../common/theme/dynamic-type";

/**
 * At AX2 a New Transaction posting shared its row with the amount controls and
 * its account read "Asse…cking" / "Ex…ries" (w21/029). From the shared stacking
 * threshold the account takes its own lines, head-ellipsized so the leaf
 * survives, with the amount controls under it at the trailing edge. Checked on
 * the source: the row lives in a screen the unit runner cannot render.
 */
const source = fs.readFileSync(
  path.join(__dirname, "..", "multi-postings-transaction-screen.tsx"),
  "utf8",
);
const block = (name: string) => {
  const start = source.indexOf(`    ${name}: {`);
  return start < 0 ? "" : source.slice(start, source.indexOf("},", start));
};

describe("New Transaction posting row at large text sizes", () => {
  it("stacks from the shared threshold, which AX2 crosses", () => {
    expect(
      source.includes("const stacked = prefersStackedLayout(fontScale);"),
    ).toBe(true);
    expect(prefersStackedLayout(2)).toBe(true);
    expect(prefersStackedLayout(1)).toBe(false);
    expect(block("postingRowStacked").includes('flexDirection: "column"')).toBe(
      true,
    );
    expect(source.includes("stacked && styles.postingRowStacked")).toBe(true);
  });

  it("keeps the account's leaf on up to two lines", () => {
    expect(source.includes("numberOfLines={stacked ? 2 : 1}")).toBe(true);
    expect(source.includes('ellipsizeMode={stacked ? "head" : "middle"}')).toBe(
      true,
    );
    // The row's flex: 1 wrapper would collapse in the column.
    expect(
      source.includes(
        "style={stacked ? undefined : styles.postingAccountWrap}",
      ),
    ).toBe(true);
  });

  it("puts the amount controls under the account and remeasures live", () => {
    expect(
      block("postingAmountWrapStacked").includes('alignSelf: "flex-end"'),
    ).toBe(true);
    expect(source.includes("key={`posting-account-${fontScale}`}")).toBe(true);
  });
});
