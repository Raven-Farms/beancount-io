import fs from "fs";
import path from "path";

// w21/606: on Android the JavaScript tab bar floats over the screen, and the
// lists had no bottom padding for it, so the last file or account row and
// Transactions' Retry sat under the pill and taps hit the bar. Source check (the
// navigator needs the native runtime).
const tabs = fs
  .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
  .replace(/\s+/g, "");

describe("the Android tab bar", () => {
  it("is positioned over the screen, and the scenes end above it", () => {
    const android = tabs.slice(tabs.indexOf("functionJavaScriptTabNavigator("));
    expect(android.includes(`position:"absolute"`)).toBe(true);
    expect(
      android.includes(
        "sceneStyle:{paddingBottom:TAB_BAR_CONTENT_HEIGHT+bottomInset}",
      ),
    ).toBe(true);
  });

  it("uses the one height for its own box and the scenes", () => {
    expect(tabs.includes("height:TAB_BAR_CONTENT_HEIGHT+bottomInset")).toBe(
      true,
    );
    expect(tabs.includes(`from"./tab-bar-metrics"`)).toBe(true);
    expect(tabs.includes("constTAB_BAR_CONTENT_HEIGHT=")).toBe(false);
  });
});
