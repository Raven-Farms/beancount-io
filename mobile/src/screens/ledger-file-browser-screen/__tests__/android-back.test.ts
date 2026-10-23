import fs from "fs";
import path from "path";

// w21/274: the folder stack is component state, so Android's Back left the
// Files tab from any depth. The screen runs hooks this runner cannot execute,
// so the wiring is checked on its source.
describe("the file browser's Back and tab re-tap", () => {
  const source = fs
    .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
    .replace(/\s+/g, "");

  it("goes up a folder on hardware Back, only while in a sub-folder", () => {
    const from = source.indexOf("useFocusEffect(");
    expect(from === -1).toBe(false);
    const effect = source.slice(from, source.indexOf("[goUp,inSubDir],", from));
    expect(
      effect.startsWith(
        "useFocusEffect(useCallback(()=>{if(!inSubDir)returnundefined;",
      ),
    ).toBe(true);
    expect(
      effect.includes('BackHandler.addEventListener("hardwareBackPress"'),
    ).toBe(true);
    // Consumes the press, so the tab is not left; removes it on blur.
    expect(effect.includes("goUp();returntrue;")).toBe(true);
    expect(effect.includes("subscription.remove()")).toBe(true);
    expect(
      source.includes("stack:popPathStack(pathStackForLedger(prev,ledgerId))"),
    ).toBe(true);
  });

  it("returns to the root when the focused Files tab is tapped again", () => {
    expect(source.includes('navigation.addListener("tabPress"')).toBe(true);
    expect(
      source.includes(
        'if(navigation.isFocused()){setPathState({ledgerId,stack:[""]});}',
      ),
    ).toBe(true);
  });
});
