import fs from "fs";
import path from "path";

// w21/108: a library pick returned the original HEIC, which the parsing
// models cannot read, so every iPhone photo failed as unreadable.
describe("Choose from photos", () => {
  it("asks iOS for a JPEG-compatible representation", () => {
    const source = fs
      .readFileSync(
        path.join(__dirname, "..", "receipt-capture-screen.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(
      source.includes(
        "preferredAssetRepresentationMode:ImagePicker.UIImagePickerPreferredAssetRepresentationMode.Compatible",
      ),
    ).toBe(true);
  });
});
