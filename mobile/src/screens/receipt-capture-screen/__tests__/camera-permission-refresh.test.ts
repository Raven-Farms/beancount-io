import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";

// w21/283: on Android, granting camera access in Settings left the receipt
// screen on "Camera access is needed" until it was reopened, since the hook
// reads the permission once. The component runs native hooks this runner
// cannot execute, so the wiring is checked on its source.
describe("the receipt camera's permission", () => {
  const source = fs
    .readFileSync(path.join(__dirname, "..", "camera-view.tsx"), "utf8")
    .replace(/\s+/g, "");

  it("is read again when the app returns to the foreground", () => {
    expect(
      source.includes(
        'AppState.addEventListener("change",(state)=>{if(state==="active")voidgetPermission().catch(()=>undefined);})',
      ),
    ).toBe(true);
    expect(
      source.includes("const[permission,requestPermission,getPermission]="),
    ).toBe(true);
    expect(source.includes("subscription.remove()")).toBe(true);
  });

  it("labels the button by what it does", () => {
    expect(
      source.includes(
        'permission.canAskAgain?t("receiptAllowCamera"):t("receiptOpenSettings")',
      ),
    ).toBe(true);
    expect(en.receiptAllowCamera).toBe("Allow Camera");
  });
});
