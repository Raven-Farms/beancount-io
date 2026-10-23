import { bqlPayeeEquals } from "../screens/merchant-detail-screen/selectors/escape-bql-string";

// The ledger's BQL engine reads string literals with no escapes, so `\"` in a
// payee was a syntax error and the merchant header disappeared (w21/032).
describe("bqlPayeeEquals", () => {
  it("compares an ordinary payee exactly, as before", () => {
    expect(bqlPayeeEquals("MiniMax Group Inc.")).toBe(
      'payee = "MiniMax Group Inc."',
    );
    expect(bqlPayeeEquals("Lowe's")).toBe('payee = "Lowe\'s"');
    expect(bqlPayeeEquals("Ethereum 2.0")).toBe('payee = "Ethereum 2.0"');
  });

  it("matches a payee with a double quote by an anchored regex", () => {
    expect(bqlPayeeEquals('qa O\'Reilly "Q" Café')).toBe(
      'payee ~ "^qa O\'Reilly \\x22Q\\x22 Café$"',
    );
  });

  it("escapes regex metacharacters and backslashes in that form", () => {
    expect(bqlPayeeEquals('12" Sub (Co.)\\')).toBe(
      'payee ~ "^12\\x22 Sub \\(Co\\.\\)\\\\$"',
    );
  });

  it("never emits the backslash-quote escape the engine rejects", () => {
    for (const payee of ['a"b', 'x\\"y', '"']) {
      expect(bqlPayeeEquals(payee).includes('\\"')).toBe(false);
    }
  });
});
