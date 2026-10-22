import { matchBrand } from "../index";

// w21/270: a statement line that names the processor before `*` got the
// processor's logo, and "#1" bypassed the common-word guard.
describe("processor and aggregator prefixes", () => {
  it("shows the merchant behind a payment processor", () => {
    expect(matchBrand("PAYPAL *NETFLIX")).toBe("netflix.com");
    expect(matchBrand("PAYPAL *SPOTIFY")).toBe("spotify.com");
    expect(matchBrand("PP*NETFLIX")).toBe("netflix.com");
  });

  it("gives an unrecognised PayPal merchant no logo, not PayPal's", () => {
    expect(matchBrand("PAYPAL *LOCALBAKERY")).toBe(null);
    expect(matchBrand("paypal")).toBe("paypal.com");
    expect(matchBrand("PAYPAL *")).toBe("paypal.com");
  });

  it("reads an aggregator's star as a space", () => {
    expect(matchBrand("GOOGLE *YouTube Premium")).toBe("youtube.com");
    expect(matchBrand("UBER *EATS")).toBe("ubereats.com");
    expect(matchBrand("UBER* EATS PENDING")).toBe("ubereats.com");
    expect(matchBrand("UBER *TRIP")).toBe("uber.com");
    expect(matchBrand("AMAZON *MKTPLACE")).toBe("amazon.com");
  });

  // w21/407: "apple" is a common word that matches only alone, so a tail we do
  // not know lost the Apple logo along with the rest of the name.
  it("falls back to an aggregator's own brand for a tail it does not know", () => {
    expect(matchBrand("APPLE *ICLOUD")).toBe("apple.com");
    expect(matchBrand("APPLE *SUBSCRIPTION")).toBe("apple.com");
    expect(matchBrand("Apple *Apple Music")).toBe("apple.com");
    expect(matchBrand("APPLE* BILL")).toBe("apple.com");
    expect(matchBrand("APPLE *ITUNES")).toBe("apple.com");
    expect(matchBrand("UBER *SOMETHING")).toBe("uber.com");
    // A processor's unknown merchant still has no logo, and a specific tail wins.
    expect(matchBrand("PAYPAL *NETFLIX")).toBe("netflix.com");
    expect(matchBrand("PAYPAL *LOCALBAKERY")).toBe(null);
    expect(matchBrand("UBER *EATS")).toBe("ubereats.com");
  });

  it("does not give Apple's logo to a longer name that merely starts with apple", () => {
    expect(matchBrand("Apple Valley Dental")).toBe(null);
  });
});

describe("# store numbers", () => {
  it("cuts a store number but not a name's ordinal", () => {
    expect(matchBrand("United #1 Plumbing")).toBe(null);
    expect(matchBrand("TARGET #00012345")).toBe("target.com");
    expect(matchBrand("CHASE #4821")).toBe("chase.com");
    expect(matchBrand("STARBUCKS #1234")).toBe("starbucks.com");
  });
});

// w21/333: any letter counted as a word character (w21/172), but Han, kana and
// Thai write no spaces between words, so a brand beside them stopped matching.
describe("a brand beside Chinese, Japanese or Thai text", () => {
  it("matches", () => {
    expect(matchBrand("Amazon购物")).toBe("amazon.com");
    expect(matchBrand("京东Amazon旗舰店")).toBe("amazon.com");
    expect(matchBrand("Netflix会员")).toBe("netflix.com");
    expect(matchBrand("支付宝Starbucks")).toBe("starbucks.com");
    expect(matchBrand("Uberタクシー")).toBe("uber.com");
    expect(matchBrand("Spotifyสมาชิก")).toBe("spotify.com");
  });

  it("still refuses a brand inside a longer Latin or accented word", () => {
    expect(matchBrand("Café Amazonía")).toBe(null);
    expect(matchBrand("Amazonas")).toBe(null);
    expect(matchBrand("Sub-Uberia")).toBe(null);
  });
});
