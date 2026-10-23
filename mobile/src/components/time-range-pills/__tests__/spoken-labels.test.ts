import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";
import { translationLocales } from "../../../translations/__tests__/locale-parity";
import { rangePillText, RANGE_LABEL_KEYS } from "../../../common/series-util";

// w21/560: the pills were named by their abbreviations, which VoiceOver read as
// "1 M" and spelled out ("Y T D").
const t = (key: string) => (en as unknown as Record<string, string>)[key];
const SPOKEN = [
  "rangeSpoken1M",
  "rangeSpoken3M",
  "rangeSpoken6M",
  "rangeSpokenYTD",
  "rangeSpoken1Y",
  "rangeSpokenLastYear",
  "rangeSpokenAll",
];

describe("the range pills' spoken names", () => {
  it("are full names, not the abbreviations on the pill", () => {
    expect(rangePillText(t, RANGE_LABEL_KEYS["1M"])).toEqual({
      label: "1M",
      spoken: "1 month",
    });
    expect(rangePillText(t, RANGE_LABEL_KEYS.YTD).spoken).toBe("Year to date");
    expect(rangePillText(t, RANGE_LABEL_KEYS["1Y"]).spoken).toBe("1 year");
    expect(rangePillText(t, RANGE_LABEL_KEYS.ALL).spoken).toBe("All time");
    expect(rangePillText(t, "rangeLastYear").spoken).toBe("Last year");
  });

  it("fall back to the label for a pill with no spoken name", () => {
    expect(rangePillText((key) => key.toUpperCase(), "somethingElse")).toEqual({
      label: "SOMETHINGELSE",
      spoken: "SOMETHINGELSE",
    });
  });

  it("exist in every language", () => {
    for (const locale of translationLocales()) {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const catalog = require(`../../../translations/${locale}`)[locale];
      for (const key of SPOKEN) {
        expect(typeof catalog[key]).toBe("string");
        expect(catalog[key].length > 0).toBe(true);
      }
    }
  });

  it("is what the pill announces, from the option", () => {
    const pill = fs
      .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
      .replace(/\s+/g, "");
    expect(
      pill.includes("accessibilityLabel={option.spoken??option.label}"),
    ).toBe(true);
  });
});
