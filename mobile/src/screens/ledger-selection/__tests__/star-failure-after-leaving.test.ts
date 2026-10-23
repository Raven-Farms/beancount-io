import fs from "fs";
import path from "path";

// w21/300: tapping a star on a slow connection and going Back left the failed
// toggle's "Couldn't complete that action" toast over the next screen. The
// screen uses hooks this runner cannot execute, so the wiring is checked on its
// source.
describe("Browse ledgers' star failure", () => {
  const source = fs
    .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
    .replace(/\s+/g, "");

  it("toasts only while the screen is still mounted", () => {
    expect(
      source.includes(
        'constshowError=()=>{if(!mounted.current)return;toast.showToast({message:t("discoveryActionError"),type:"error"});};',
      ),
    ).toBe(true);
  });

  it("routes the star's rejection through that check", () => {
    expect(source.includes("voidstore.toggle(item).catch(showError);")).toBe(
      true,
    );
  });
});
