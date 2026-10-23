import fs from "fs";
import path from "path";
import { EXAMPLE_IDS } from "../../../common/guest/guest-state";
import { EXAMPLE_TITLE_KEYS } from "../example-titles";
import { en } from "../../../translations/en";

// w21/294: the guest drawer listed the examples by raw id ("nvidia") although
// the chooser had shown "Company finances". The layout and the drawer use
// hooks this runner cannot execute, so the wiring is checked on source.
describe("the guest drawer's example names", () => {
  const read = (...parts: string[]) =>
    fs
      .readFileSync(path.join(__dirname, "..", "..", "..", ...parts), "utf8")
      .replace(/\s+/g, "");

  it("has a chooser title for every example", () => {
    expect(EXAMPLE_TITLE_KEYS.length).toBe(EXAMPLE_IDS.length);
    expect(en.guestExample1).toBe("Company finances");
  });

  it("shows the chooser's title with the id beneath it", () => {
    const tabs = read("screens", "examples", "example-tabs.tsx");
    expect(
      tabs.includes("name:t(EXAMPLE_TITLE_KEYS[index]),subtitle:id,"),
    ).toBe(true);
    const selector = read("screens", "examples", "example-selector.tsx");
    expect(selector.includes("consttitles=EXAMPLE_TITLE_KEYS;")).toBe(true);
    const drawer = read("components", "ledger-drawer", "ledger-drawer.tsx");
    expect(
      drawer.includes(
        "{item.subtitle?(<Textstyle={styles.caption}>{item.subtitle}</Text>):null}",
      ),
    ).toBe(true);
  });
});
