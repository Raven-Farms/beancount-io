import { capitalizeAccountPrefill } from "../create-account-prefill";
import { validateAccountName } from "../../open-account-screen/account-name";

const opensValid = (query: string) =>
  validateAccountName(`Assets:${capitalizeAccountPrefill(query)}`).ok;

describe("capitalizeAccountPrefill", () => {
  it("capitalizes a lowercase Latin query so Open Account starts valid", () => {
    expect(capitalizeAccountPrefill("groceryboxw")).toBe("Groceryboxw");
    expect(validateAccountName("Assets:groceryboxw").ok).toBe(false);
    expect(opensValid("groceryboxw")).toBe(true);
  });

  it("leaves an already-capitalized query unchanged", () => {
    expect(capitalizeAccountPrefill("Groceryboxw")).toBe("Groceryboxw");
  });

  it("capitalizes only the first letter of each component", () => {
    expect(capitalizeAccountPrefill("food:dining-out")).toBe("Food:Dining-out");
    expect(opensValid("food:dining-out")).toBe(true);
  });

  it("capitalizes an accented Latin initial", () => {
    expect(capitalizeAccountPrefill("épargne")).toBe("Épargne");
  });

  it("passes caseless scripts, digits, and letters without a single uppercase form through", () => {
    expect(capitalizeAccountPrefill("日本")).toBe("日本");
    expect(capitalizeAccountPrefill("401k")).toBe("401k");
    expect(capitalizeAccountPrefill("ßteuer")).toBe("ßteuer");
  });

  it("does not repair a name that is invalid for another reason", () => {
    expect(capitalizeAccountPrefill("cash box")).toBe("Cash box");
    expect(opensValid("cash box")).toBe(false);
  });

  it("keeps an empty or whitespace-only query as it is", () => {
    expect(capitalizeAccountPrefill("")).toBe("");
    expect(capitalizeAccountPrefill("   ")).toBe("   ");
  });

  // w21/260: only Latin initials were capitalised, so ru, uk and bg users landed
  // on a name the form refused.
  it("capitalizes Cyrillic and Greek initials too", () => {
    expect(capitalizeAccountPrefill("продукты")).toBe("Продукты");
    expect(capitalizeAccountPrefill("їжа")).toBe("Їжа");
    expect(capitalizeAccountPrefill("храна")).toBe("Храна");
    expect(capitalizeAccountPrefill("φαγητό")).toBe("Φαγητό");
    expect(opensValid("продукты")).toBe(true);
    expect(opensValid("φαγητό")).toBe(true);
    expect(opensValid("їжа:ресторан")).toBe(true);
  });

  it("drops the space after a colon, so each component starts a name", () => {
    expect(capitalizeAccountPrefill("expenses: food")).toBe("Expenses:Food");
    expect(opensValid("expenses: food")).toBe(true);
  });

  it("leaves ß, the Turkish dotless i and caseless text as they were", () => {
    expect(capitalizeAccountPrefill("ßteuer")).toBe("ßteuer");
    expect(capitalizeAccountPrefill("\u0131\u015f")).toBe("\u0131\u015f");
    expect(capitalizeAccountPrefill("i\u015f")).toBe("I\u015f");
    expect(capitalizeAccountPrefill("日本:食費")).toBe("日本:食費");
  });
});

// w21/531: `gym` offered Create for a closed `Expenses:Gym`, which Open Account
// then refused.
describe("createdAccountName", () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { createdAccountName } = require("../create-account-prefill");
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { closedAccountNamed } = require("../../../common/account-close-dates");

  it("composes the name Open Account will, under the picker's root", () => {
    expect(createdAccountName("gym", "Expenses")).toBe("Expenses:Gym");
    expect(createdAccountName("my savings", "Assets")).toBe("Assets:MySavings");
    expect(createdAccountName("liabilities:card", "Expenses")).toBe(
      "Liabilities:Card",
    );
  });

  it("follows a ledger's renamed roots", () => {
    expect(createdAccountName("gym", "Expenses", { expenses: "Gastos" })).toBe(
      "Gastos:Gym",
    );
  });

  it("finds the closed account a short name would recreate", () => {
    const closeDates = new Map([["Expenses:Gym", "2026-09-01"]]);
    expect(closedAccountNamed("gym", "2026-10-22", closeDates)).toBe(null);
    expect(
      closedAccountNamed(
        createdAccountName("gym", "Expenses"),
        "2026-10-22",
        closeDates,
      ),
    ).toEqual({ account: "Expenses:Gym", closedAt: "2026-09-01" });
  });
});
