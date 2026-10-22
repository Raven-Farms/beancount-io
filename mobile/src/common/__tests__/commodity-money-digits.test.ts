import {
  formatMoneyWithCurrency,
  formatSignedMoneyWithCurrency,
} from "../number-utils";
import { isFiatCurrency } from "../currency-util";

// w21/595: in a BTC ledger, Accounts, Spending, Reports and merchant totals
// rounded BTC to two decimals: "Wallet (own) 0.00 BTC" for 0.004.
describe("money in a commodity", () => {
  it("keeps the digits the value has, from two up to eight", () => {
    expect(formatMoneyWithCurrency(0.004, "BTC")).toBe("0.004 BTC");
    expect(formatMoneyWithCurrency(0.003, "BTC")).toBe("0.003 BTC");
    expect(formatMoneyWithCurrency(1.507, "BTC")).toBe("1.507 BTC");
    expect(formatMoneyWithCurrency(1, "BTC")).toBe("1.00 BTC");
    expect(formatMoneyWithCurrency(0.00012345, "BTC")).toBe("0.00012345 BTC");
    expect(formatMoneyWithCurrency(0.1 + 0.2, "BTC")).toBe("0.30 BTC");
    expect(formatSignedMoneyWithCurrency(-0.0042, "BTC")).toBe("-0.0042 BTC");
    expect(formatSignedMoneyWithCurrency(0.004, "BTC", true)).toBe(
      "+0.004 BTC",
    );
  });

  it("is the tree the note describes", () => {
    const rows = [1.507, 0.004, 0.003].map((value) =>
      formatMoneyWithCurrency(value, "BTC"),
    );
    expect(rows).toEqual(["1.507 BTC", "0.004 BTC", "0.003 BTC"]);
  });

  it("leaves national currencies at their minor unit", () => {
    expect(isFiatCurrency("USD")).toBe(true);
    expect(isFiatCurrency("JPY")).toBe(true);
    expect(isFiatCurrency("BTC")).toBe(false);
    expect(formatMoneyWithCurrency(0.004, "USD")).toBe("$0.00");
    expect(formatMoneyWithCurrency(1500, "JPY")).toBe("¥1,500");
    // Three minor units for the dinar, symbol and all.
    expect(formatMoneyWithCurrency(12.345, "KWD").endsWith("12.345")).toBe(
      true,
    );
  });

  it("keeps a custom commodity at two decimals when it needs no more", () => {
    expect(formatMoneyWithCurrency(551620, "MUSD")).toBe("551,620.00 MUSD");
    expect(formatMoneyWithCurrency(0, "MSEK")).toBe("0.00 MSEK");
  });

  it("still honours a recorded scale beyond what the value shows", () => {
    expect(formatMoneyWithCurrency(1, "BTC", 4)).toBe("1.0000 BTC");
  });
});
