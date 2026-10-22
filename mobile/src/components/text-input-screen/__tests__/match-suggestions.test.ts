import { matchSuggestions } from "../match-suggestions";

// w21/257: the suggestions list used `toLowerCase().includes()` and the raw
// string as its key, so "iş" never matched "İşBank ATM", a composed "café"
// never matched an NFD "Café Central", and the two spellings were two rows.
describe("matchSuggestions", () => {
  it("matches a Turkish capital İ by its lower-case spelling", () => {
    expect(matchSuggestions(["İşBank ATM"], "iş", 30)).toEqual(["İşBank ATM"]);
    expect(matchSuggestions(["İşBank ATM"], "işbank", 30)).toEqual([
      "İşBank ATM",
    ]);
  });

  it("matches NFD text with an NFC query, and the other way round", () => {
    const nfd = "Café Central";
    expect(matchSuggestions([nfd], "café", 30)).toEqual([nfd]);
    expect(matchSuggestions(["Café Central"], "café", 30)).toEqual([
      "Café Central",
    ]);
  });

  it("shows the NFC and NFD spellings of one payee as one row, as first written", () => {
    expect(matchSuggestions(["Café Central", "Café Central"], "", 30)).toEqual([
      "Café Central",
    ]);
  });

  it("keeps the plain behaviour: trim, drop empties, substring, limit", () => {
    expect(
      matchSuggestions([" Coffee ", "", "  ", "Tea", "coffee"], "cof", 30),
    ).toEqual(["Coffee", "coffee"]);
    expect(matchSuggestions(["a", "b", "c"], "", 2)).toEqual(["a", "b"]);
    expect(matchSuggestions(undefined, "x", 5)).toEqual([]);
    expect(matchSuggestions(["Tea"], "  ", 5)).toEqual(["Tea"]);
  });
});
