import fs from "fs";
import path from "path";
import { groupAccountsByRoot } from "../../../common/ledger-meta-utils";
import { visibleAccountSections, withParentAccounts } from "../picker-sections";

// The Transactions filter could not choose a category such as Expenses:Food:
// the picker lists only opened accounts (w21/036).
const OPENED = [
  "Assets:Cash",
  "Expenses:Food:Coffee",
  "Expenses:Food:Groceries",
  "Expenses:Food:Restaurants",
  "Expenses:Transport",
];

describe("withParentAccounts", () => {
  it("adds each parent once, just before its first child", () => {
    expect(withParentAccounts(OPENED)).toEqual([
      "Assets:Cash",
      "Expenses:Food",
      "Expenses:Food:Coffee",
      "Expenses:Food:Groceries",
      "Expenses:Food:Restaurants",
      "Expenses:Transport",
    ]);
  });

  it("adds every level of a deep account, and nothing for a shallow one", () => {
    expect(withParentAccounts(["Assets:US:Bank:Checking"])).toEqual([
      "Assets:US",
      "Assets:US:Bank",
      "Assets:US:Bank:Checking",
    ]);
    expect(withParentAccounts(["Assets:Cash"])).toEqual(["Assets:Cash"]);
  });

  it("lets a search for the category find the category first", () => {
    const accounts = withParentAccounts(OPENED);
    const [results] = visibleAccountSections(
      groupAccountsByRoot(accounts),
      accounts,
      "Expenses:Food",
      null,
    );
    expect(results!.data[0]).toBe("Expenses:Food");
  });

  it("offers parents to the filter picker only", () => {
    const screen = fs.readFileSync(
      path.join(__dirname, "..", "account-picker-screen.tsx"),
      "utf8",
    );
    // Posting pickers get the opened accounts still open on the entry's date
    // (w21/045); only the filter picker adds parents.
    expect(
      screen.includes(
        'return type === "filter"\n      ? withParentAccounts(opened)\n      : openOn(opened,',
      ),
    ).toBe(true);
  });
});
