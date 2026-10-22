import {
  exactPayeeFilter,
  filterExactPayee,
} from "../screens/merchant-detail-screen/selectors/filter-exact-payee";

describe("filterExactPayee", () => {
  const entries = [
    { payee: "Uber", id: 1 },
    { payee: "Uber Eats", id: 2 },
    { payee: "uber", id: 3 },
    { payee: " Uber ", id: 4 },
    { payee: null, id: 5 },
    { payee: "", id: 6 },
  ];

  it("keeps only exact payee matches after trim", () => {
    expect(filterExactPayee(entries, "Uber").map((e) => e.id)).toEqual([1, 4]);
  });

  it("does not match a substring payee like Uber Eats", () => {
    expect(filterExactPayee(entries, "Uber").map((e) => e.payee)).toEqual([
      "Uber",
      " Uber ",
    ]);
  });

  it("matches punctuated payees literally, without normalizing periods", () => {
    const punctuated = [
      { payee: "Ethereum 2.0", id: 1 },
      { payee: "Ethereum 2 0", id: 2 },
      { payee: "Lowe's", id: 3 },
      { payee: "Lowes", id: 4 },
      { payee: "MiniMax Group Inc.", id: 5 },
      { payee: "MiniMax Group Inc", id: 6 },
    ];
    expect(
      filterExactPayee(punctuated, "Ethereum 2.0").map((e) => e.id),
    ).toEqual([1]);
    expect(filterExactPayee(punctuated, "Lowe's").map((e) => e.id)).toEqual([
      3,
    ]);
    expect(
      filterExactPayee(punctuated, "MiniMax Group Inc.").map((e) => e.id),
    ).toEqual([5]);
  });

  it("is case-sensitive and rejects empty targets", () => {
    expect(filterExactPayee(entries, "uber").map((e) => e.id)).toEqual([3]);
    expect(filterExactPayee(entries, "   ")).toEqual([]);
    expect(filterExactPayee(entries, "")).toEqual([]);
  });
});

// w21/181: free-text filtering paged through longer names ("Ace" among "Ace
// Deli") and stopped at 500, so the merchant's own rows vanished.
describe("exactPayeeFilter", () => {
  it("anchors every spelling, escaped, and pads for trailing spaces", () => {
    expect(exactPayeeFilter(["QA Ace"])).toBe('payee:"^\\s*(?:QA Ace)\\s*$"');
    expect(exactPayeeFilter(["Lowe's", "Ethereum 2.0", 'A "B"'])).toBe(
      'payee:"^\\s*(?:Lowe\'s|Ethereum 2\\.0|A \\x22B\\x22)\\s*$"',
    );
  });

  // w21/361: the ledger service refuses a filter pattern over 256 characters,
  // which failed the whole journal for a merchant with long merged spellings.
  it("merges spellings that differ only in case or trailing space", () => {
    expect(exactPayeeFilter(["QA Ace", "qa ace", "QA Ace ", "Qa ACE"])).toBe(
      'payee:"^\\s*(?:QA Ace)\\s*$"',
    );
  });

  it("stays under the server's pattern limit, falling back to the primary spelling as text", () => {
    const long = "ACME INTERNATIONAL PAYMENT PROCESSING SERVICES 0123456789";
    const spellings = [
      long,
      long.toLowerCase(),
      `${long} `,
      `${long} EU`,
      `${long} UK`,
      `${long} DE`,
      `${long} FR`,
      `${long} IT`,
    ];
    const filter = exactPayeeFilter(spellings)!;
    // Six distinct spellings of 57-60 characters do not fit in 256, so the
    // primary one is matched as text instead.
    expect(filter).toBe(`"${long}"`);
    // Case variants alone collapse to one alternative, which fits.
    expect(
      exactPayeeFilter([long, long.toLowerCase(), `${long} `])!.startsWith(
        'payee:"^',
      ),
    ).toBe(true);
  });

  it("is nothing for no payee", () => {
    expect(exactPayeeFilter([" "])).toBe(undefined);
  });

  it("is what merchant detail pages with", () => {
    const screen = require("fs").readFileSync(
      require("path").join(
        __dirname,
        "..",
        "screens",
        "merchant-detail-screen",
        "merchant-detail-screen.tsx",
      ),
      "utf8",
    );
    expect(screen.includes("exactPayeeFilter(spellings), [spellings]")).toBe(
      true,
    );
  });
});
