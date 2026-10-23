import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";
import { cameraPromptPending } from "../receipt-utils";

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

// w21/637: an undetermined permission is `granted: false`, so the first visit
// drew the denied copy behind the system camera prompt.
describe("the receipt camera's first prompt", () => {
  const undetermined = { granted: false, canAskAgain: true };

  it("waits on the prompt with the letterbox, then shows a refusal", () => {
    expect(cameraPromptPending(undetermined, false)).toBe(true);
    expect(cameraPromptPending(undetermined, true)).toBe(false);
    expect(
      cameraPromptPending({ granted: true, canAskAgain: true }, false),
    ).toBe(false);
    // A refusal on record that cannot be asked again shows at once.
    expect(
      cameraPromptPending({ granted: false, canAskAgain: false }, false),
    ).toBe(false);
  });

  it("is what the screen renders the letterbox for, until the request returns", () => {
    const source = fs
      .readFileSync(path.join(__dirname, "..", "camera-view.tsx"), "utf8")
      .replace(/\s+/g, "");
    expect(
      source.includes(
        "if(!permission||cameraPromptPending(permission,prompted))",
      ),
    ).toBe(true);
    expect(source.includes(".finally(()=>setPrompted(true))")).toBe(true);
  });
});
