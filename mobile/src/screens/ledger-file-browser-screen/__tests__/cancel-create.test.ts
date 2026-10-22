import fs from "fs";
import path from "path";

/**
 * w21/376: cancelling New File while its folder lookup was pending still
 * created the file and opened it, and the lookup had no bound or busy state.
 * Source checks: the screen needs the native runtime.
 */
const read = (relative: string) =>
  fs
    .readFileSync(path.join(__dirname, "../../..", relative), "utf8")
    .replace(/\s+/g, "");

describe("cancelling New File during the folder lookup", () => {
  const screen = read("screens/ledger-file-browser-screen/index.tsx");

  it("voids the attempt, so nothing is created or opened", () => {
    expect(
      screen.includes(
        "constcancelCreate=()=>{createAttemptRef.current+=1;createInFlightRef.current=false;setLookingUp(false);setCreateModalVisible(false);};",
      ),
    ).toBe(true);
    expect(screen.includes("onCancel={cancelCreate}")).toBe(true);
    // Checked after the lookup, on both its outcomes, before the dialog closes.
    expect(
      screen.includes("if(createAttemptRef.current!==attempt)return;"),
    ).toBe(true);
    const guard = screen.lastIndexOf(
      "if(createAttemptRef.current!==attempt)return;",
    );
    expect(guard < screen.indexOf("setCreateModalVisible(false);try{")).toBe(
      true,
    );
  });

  it("bounds the lookup and shows a busy, disabled Create while it runs", () => {
    expect(screen.includes("CONNECTION_TIMEOUT_MS")).toBe(true);
    expect(screen.includes("settleWithin(")).toBe(true);
    expect(screen.includes("busy={lookingUp}")).toBe(true);
    const modal = read("components/text-input-modal/index.tsx");
    expect(modal.includes("validation!==true||busy")).toBe(true);
    expect(
      modal.includes("accessibilityState={{disabled:isConfirmDisabled,busy}}"),
    ).toBe(true);
  });
});
