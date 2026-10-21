import fs from "fs";
import path from "path";
import { en } from "../translations/en";
import { zh } from "../translations/zh";

/**
 * w21/118: Merchants, merchant detail and Entry Context appended the raw
 * Apollo text to a prefix ("加载商户失败：Network request failed"); two had no
 * Retry, and Entry Context's error hid cached context.
 */
const read = (...parts: string[]) =>
  fs.readFileSync(path.join(__dirname, "..", ...parts), "utf8");

describe("load errors on Merchants, merchant detail and Entry Context", () => {
  it("are whole translated sentences", () => {
    expect(en.merchantsLoadError).toBe("Failed to load merchants");
    expect(zh.merchantsLoadError.endsWith("：")).toBe(false);
    expect(en.merchantDetailLoadError.endsWith(": ")).toBe(false);
  });

  it("never append the error's message, and offer Retry", () => {
    const merchants = read(
      "screens",
      "merchants-screen",
      "merchants-screen.tsx",
    );
    expect(merchants.includes("{error.message}")).toBe(false);
    expect(merchants.includes("<CardLoadFailure onRetry=")).toBe(true);
    // A failed recurrence series no longer empties the directory.
    expect(merchants.includes("seriesError")).toBe(false);

    const detail = read(
      "screens",
      "merchant-detail-screen",
      "merchant-detail-screen.tsx",
    );
    expect(detail.includes("listError.message")).toBe(false);
    expect(detail.includes("statsMessage")).toBe(false);

    const context = read(
      "screens",
      "transactions-screen",
      "entry-context",
      "index.tsx",
    );
    expect(context.includes("entryError.message")).toBe(false);
    expect(context.includes("if (entryError && !entryContext) {")).toBe(true);
    expect(context.includes('t("staleDataNotice")')).toBe(true);
  });
});
