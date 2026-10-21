import fs from "fs";
import path from "path";
import { isolateLtr } from "../bidi";

// w21/095: in Persian, "مانده: -$1,234.50" rendered as `1,234.50$- :مانده`,
// the sign and symbol pulled to the wrong side of the number.
describe("isolateLtr", () => {
  it("wraps an amount in a left-to-right isolate", () => {
    expect(isolateLtr("-$1.00")).toBe("⁦-$1.00⁩");
  });

  it("is used for every amount the account journal puts in a sentence", () => {
    const row = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "..",
        "screens",
        "account-detail-screen",
        "components",
        "account-entry-row.tsx",
      ),
      "utf8",
    );
    expect(row.includes('`${t("balance")}: ${isolateLtr(balanceText)}`')).toBe(
      true,
    );
    expect(row.includes("amount: isolateLtr(detail.offBy)")).toBe(true);
    expect(row.includes('`${t("balance")} ${isolateLtr(detail.amount)}`')).toBe(
      true,
    );
  });
});
