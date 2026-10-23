import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";

// w21/557: "Remove posting" existed only as a swipe action, which VoiceOver
// reads as a focus move, so a posting added by mistake could not be removed.
// Source checks (the screen needs the native runtime).
const screen = fs
  .readFileSync(
    path.join(__dirname, "..", "multi-postings-transaction-screen.tsx"),
    "utf8",
  )
  .replace(/\s+/g, "");

describe("the posting row's remove action for VoiceOver", () => {
  it("offers Remove posting as a named action on a removable row only", () => {
    expect(
      screen.includes(
        'accessibilityActions={canRemove?[{name:"delete",label:t("removePosting")}]:undefined}',
      ),
    ).toBe(true);
  });

  it("removes the posting when the action runs", () => {
    expect(
      screen.includes(
        'onAccessibilityAction={(event)=>{if(event.nativeEvent.actionName==="delete")onRemove();}}',
      ),
    ).toBe(true);
  });

  it("keeps the swipe action and its own label", () => {
    expect(
      screen.includes("renderRightActions={canRemove?renderDeleteAction"),
    ).toBe(true);
    expect(en.removePosting).toBe("Remove posting");
  });
});
