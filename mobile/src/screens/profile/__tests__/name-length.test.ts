import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";

// w21/123: a first or last name over 100 characters failed validation with no
// message, so Save did nothing.
describe("Profile name length", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "profile-screen.tsx"),
    "utf8",
  );

  it("caps the name inputs and says why when a stored name is longer", () => {
    expect(source.includes("maxLength: NAME_MAX,")).toBe(true);
    expect(
      source.includes('z.string().max(NAME_MAX, t("profileNameTooLong"))'),
    ).toBe(true);
    expect(source.includes("{nameError(errors.firstName?.message)}")).toBe(
      true,
    );
    expect(source.includes("{nameError(errors.lastName?.message)}")).toBe(true);
    expect(en.profileNameTooLong).toBe("At most 100 characters.");
  });
});
