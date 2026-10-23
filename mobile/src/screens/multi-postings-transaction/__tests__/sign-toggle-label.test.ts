import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";
import { translationLocales } from "../../../translations/__tests__/locale-parity";

// w21/561: every posting's sign toggle sounded alike, and "Selected" was the
// only clue that the sign was negative.
const screen = fs
  .readFileSync(
    path.join(__dirname, "..", "multi-postings-transaction-screen.tsx"),
    "utf8",
  )
  .replace(/\s+/g, "");

describe("the posting sign toggle's accessibility", () => {
  it("names the posting and carries the sign as its value", () => {
    expect(
      screen.includes(
        'accessibilityLabel={posting.account?t("postingSignToggle",{account:posting.account}):t("toggleAmountSign")}',
      ),
    ).toBe(true);
    expect(
      screen.includes(
        'accessibilityValue={{text:isNegative?t("signMinus"):t("signPlus"),}}',
      ),
    ).toBe(true);
    expect(screen.includes("accessibilityState={{selected:isNegative}}")).toBe(
      false,
    );
  });

  it("reads in English as the account, then the sign", () => {
    expect(en.postingSignToggle.replace("{{account}}", "Assets:Cash")).toBe(
      "Sign for Assets:Cash",
    );
    expect(en.signMinus).toBe("Minus");
    expect(en.signPlus).toBe("Plus");
  });

  it("keeps the account in every language", () => {
    for (const locale of translationLocales()) {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const catalog = require(`../../../translations/${locale}`)[locale];
      expect(catalog.postingSignToggle.includes("{{account}}")).toBe(true);
      expect(catalog.signPlus === catalog.signMinus).toBe(false);
    }
  });
});
