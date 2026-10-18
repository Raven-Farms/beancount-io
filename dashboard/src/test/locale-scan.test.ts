import { describe, expect, it } from "vitest";
import {
  staleIdenticalEntries,
  untranslatedAgainstEnglish,
  untranslatedWholeMessage,
} from "./locale-scan";

// The whole-copy guard and its allowlist, on synthetic catalogs: a message
// pasted from English whole passed every locale guard until w0/m1, and more
// than 600 such copies shipped in Receipt, Plaid and Settings.
const en = {
  "receipt.title": "Upload Receipt",
  "receipt.hint": "Drag and drop your receipt here",
  "plaid.brand": "Plaid",
  "profile.openLedger": "Open Ledger",
  "files.format": "CSV · PDF",
};

describe("untranslatedAgainstEnglish with the whole-copy check", () => {
  const scan = (
    messages: Record<string, string>,
    allowed?: (key: string) => boolean,
  ) =>
    untranslatedAgainstEnglish(
      messages,
      en,
      untranslatedWholeMessage,
      allowed,
    ).map(({ key, words }) => `${key}: ${words.join(" ")}`);

  it("reports a message copied from English whole", () => {
    expect(scan({ "receipt.title": "Upload Receipt" })).toEqual([
      "receipt.title: Upload Receipt",
    ]);
  });

  it("passes a correctly translated message", () => {
    expect(
      scan({
        "receipt.title": "Beleg hochladen",
        "receipt.hint": "Beleg hierher ziehen und ablegen",
      }),
    ).toEqual([]);
  });

  it("passes a copy that is only brand, format or notation", () => {
    expect(
      scan({ "plaid.brand": "Plaid", "files.format": "CSV · PDF" }),
    ).toEqual([]);
  });

  it("skips an allowlisted invariant and nothing else", () => {
    const messages = {
      "profile.openLedger": "Open Ledger",
      "receipt.hint": "Drag and drop your receipt here",
    };
    expect(scan(messages, (key) => key === "profile.openLedger")).toEqual([
      "receipt.hint: Drag and drop your receipt here",
    ]);
  });

  it("ignores keys English no longer has, and a missing catalog", () => {
    expect(scan({ "gone.key": "Some English words here" })).toEqual([]);
    expect(
      untranslatedAgainstEnglish(undefined, en, untranslatedWholeMessage),
    ).toEqual([]);
  });
});

describe("staleIdenticalEntries", () => {
  const catalogs = {
    de: {
      "profile.openLedger": "Open Ledger",
      "receipt.title": "Beleg hochladen",
    },
  };

  it("keeps an entry whose message is still identical to English", () => {
    expect(
      staleIdenticalEntries(
        { "de/profile.openLedger": "proper name" },
        catalogs,
        en,
      ),
    ).toEqual([]);
  });

  it("reports an entry the locale now translates", () => {
    expect(
      staleIdenticalEntries({ "de/receipt.title": "was a copy" }, catalogs, en),
    ).toEqual(["de/receipt.title"]);
  });

  it("reports an entry whose key or locale no longer exists", () => {
    // `receipt.removed` is gone from English and the locale alike, so the two
    // lookups were both undefined and compared equal.
    expect(
      staleIdenticalEntries(
        { "de/receipt.removed": "gone", "xx/profile.openLedger": "no locale" },
        catalogs,
        en,
      ),
    ).toEqual(["de/receipt.removed", "xx/profile.openLedger"]);
  });
});
