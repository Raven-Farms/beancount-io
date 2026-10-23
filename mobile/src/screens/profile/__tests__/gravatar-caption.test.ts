import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";

// w21/289: the caption "Photo from Gravatar" sat under the initials of users
// with no Gravatar, since the backend returns a Gravatar URL for everyone
// without an upload. The components use hooks this runner cannot execute, so
// the wiring is checked on their source.
describe("the Profile avatar caption", () => {
  const read = (...parts: string[]) =>
    fs
      .readFileSync(path.join(__dirname, "..", "..", "..", ...parts), "utf8")
      .replace(/\s+/g, "");
  const profile = read("screens", "profile", "profile-screen.tsx");
  const avatar = read("components", "user-avatar", "index.tsx");

  // w21/430: only the server's 404 says there is no Gravatar; a load that
  // failed offline does not.
  it("learns from the avatar when the server says there is no picture", () => {
    expect(
      avatar.includes(
        "useEffect(()=>{onFallbackChange?.(noPicture);},[noPicture,onFallbackChange]);",
      ),
    ).toBe(true);
    expect(avatar.includes("imageIsMissing(failedSource)")).toBe(true);
    expect(profile.includes("onFallbackChange={setAvatarFallback}")).toBe(true);
  });

  it("offers to add a photo instead of claiming one", () => {
    expect(
      profile.includes(
        'constgravatarCaption=avatarFallback?t("profileAddGravatar"):t("profilePhotoFromGravatar");',
      ),
    ).toBe(true);
    expect(profile.includes("accessibilityLabel={gravatarCaption}")).toBe(true);
    expect(en.profileAddGravatar).toBe("Add a photo on Gravatar");
    expect(en.profilePhotoFromGravatar).toBe("Photo from Gravatar");
  });
});
