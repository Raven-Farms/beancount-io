import fs from "fs";
import path from "path";
import { deleteConfirmationCheck } from "../delete-confirmation";

// w21/158: an exact match left Delete greyed out, unexplained, after the
// space an iOS suggestion appends.
describe("deleteConfirmationCheck", () => {
  const check = (text: string) =>
    deleteConfirmationCheck(text, "sudo delete", "Type it exactly.");

  it("accepts the phrase with a trailing or leading space", () => {
    expect(check("sudo delete")).toBe(true);
    expect(check("sudo delete ")).toBe(true);
    expect(check(" sudo delete")).toBe(true);
  });

  it("says why a wrong phrase cannot be confirmed", () => {
    expect(check("sudo delet")).toBe("Type it exactly.");
  });

  it("disables an empty field without a message", () => {
    expect(check("")).toBe(false);
    expect(check("   ")).toBe(false);
  });

  it("is what both the modal and the confirm handler check", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "main-content.tsx"),
      "utf8",
    );
    expect(source.split("deleteConfirmationCheck(").length - 1).toBe(2);
    expect(source.includes('=== t("deleteAccountConfirmPhrase")')).toBe(false);
  });
});
