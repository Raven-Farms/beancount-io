import fs from "fs";
import path from "path";
import { deriveTwoPostingSuggestions } from "../../../common/suggestion-utils";
import {
  createInitialPostings,
  updatePostingAccount,
  updatePostingAmount,
} from "../postings-utils";
import { seedPostingsFromPayee } from "../payee-seed";

// Picking a known payee in New Transaction left the default accounts, so every
// repeat entry needed two account picks; the keypad flow it replaced used to
// prefill them (w21/023).
const txn = (payee: string, from: string, to: string, amount = "42.10") => ({
  type: "Transaction",
  payee,
  postings: [
    { account: from, units: { number: `-${amount}`, currency: "USD" } },
    { account: to, units: { number: amount, currency: "USD" } },
  ],
});
const JOURNAL = [
  txn("TRADER JOES", "Liabilities:CreditCard:Visa", "Expenses:Food:Groceries"),
  txn("TRADER JOES", "Liabilities:CreditCard:Visa", "Expenses:Food:Groceries"),
  txn("CITY BUS", "Assets:Cash", "Expenses:Transport", "2.75"),
];
const history = (payee: string) =>
  deriveTwoPostingSuggestions(JOURNAL as never, payee);
const opened = () =>
  createInitialPostings("Assets:Bank:Checking", "Expenses:Food:Groceries");
const accounts = (postings: { account: string }[] | null) =>
  postings?.map((p) => p.account) ?? null;

describe("seedPostingsFromPayee", () => {
  it("brings a known payee's usual accounts into an untouched form", () => {
    const initial = opened();
    expect(
      accounts(seedPostingsFromPayee(initial, initial, history("TRADER JOES"))),
    ).toEqual(["Liabilities:CreditCard:Visa", "Expenses:Food:Groceries"]);
    expect(
      accounts(seedPostingsFromPayee(initial, initial, history("CITY BUS"))),
    ).toEqual(["Assets:Cash", "Expenses:Transport"]);
  });

  it("leaves accounts or amounts the user already changed", () => {
    const initial = opened();
    const picked = updatePostingAccount(initial, 0, "Assets:Cash");
    expect(seedPostingsFromPayee(picked, initial, history("TRADER JOES"))).toBe(
      null,
    );
    const typed = updatePostingAmount(initial, 0, "-12");
    expect(seedPostingsFromPayee(typed, initial, history("TRADER JOES"))).toBe(
      null,
    );
  });

  it("leaves the defaults for a new payee", () => {
    const initial = opened();
    expect(seedPostingsFromPayee(initial, initial, history("NEW CAFE"))).toBe(
      null,
    );
  });

  it("never touches the amounts", () => {
    const initial = opened();
    const seeded = seedPostingsFromPayee(
      initial,
      initial,
      history("TRADER JOES"),
    )!;
    expect(seeded.map((p) => p.amountInput)).toEqual(
      initial.map((p) => p.amountInput),
    );
  });

  it("is applied when the payee is picked, unless a receipt set the accounts", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "multi-postings-transaction-screen.tsx"),
      "utf8",
    );
    expect(source.includes("setSeedPayee(v);")).toBe(true);
    expect(
      source.includes("if (!prefillSourceAccount && !prefillTargetAccount) {"),
    ).toBe(true);
    expect(source.includes("seedPostingsFromPayee(")).toBe(true);
  });
});

// w21/045: a payee whose usual card was paid off and closed autofilled that
// card, and the save was refused.
describe("seedPostingsFromPayee: closed usual accounts", () => {
  const closedCard = (account: string) =>
    account !== "Liabilities:CreditCard:Visa";

  it("keeps the default on a side whose usual account is closed", () => {
    const initial = opened();
    expect(
      accounts(
        seedPostingsFromPayee(
          initial,
          initial,
          history("TRADER JOES"),
          closedCard,
        ),
      ),
    ).toEqual(["Assets:Bank:Checking", "Expenses:Food:Groceries"]);
  });

  it("changes nothing when both usual accounts are closed", () => {
    const initial = opened();
    expect(
      seedPostingsFromPayee(initial, initial, history("CITY BUS"), () => false),
    ).toBe(null);
  });
});
