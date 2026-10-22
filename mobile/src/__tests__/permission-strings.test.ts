import fs from "fs";
import path from "path";

/**
 * Config plugins run after `ios.infoPlist` and overwrite it: expo-camera
 * turned the receipt purpose string into "Allow Beancount to access your
 * camera" and added microphone use, expo-image-picker added RECORD_AUDIO, and
 * expo-secure-store added Face ID use. The app records no audio and uses no
 * biometrics (w21/016; App Review 5.1.1). A plugin's `false` removes or blocks
 * the permission; every plugin that sets a string must give the same one.
 */
type Plugin = string | [string, Record<string, unknown>];
const app = JSON.parse(
  fs.readFileSync(path.join(__dirname, "..", "..", "app.json"), "utf8"),
).expo as {
  ios: { infoPlist: Record<string, unknown> };
  locales?: Record<string, string>;
  android: { permissions?: string[] };
  plugins: Plugin[];
};
const options = (name: string) => {
  const plugin = app.plugins.find(
    (p) => (Array.isArray(p) ? p[0] : p) === name,
  );
  return Array.isArray(plugin) ? plugin[1] : {};
};

const CAMERA = "Beancount uses the camera to scan receipts.";
const PHOTOS = "Beancount accesses your photos to scan receipts.";

describe("permission strings", () => {
  it("asks for the camera and photos only to scan receipts", () => {
    expect(app.ios.infoPlist.NSCameraUsageDescription).toBe(CAMERA);
    expect(app.ios.infoPlist.NSPhotoLibraryUsageDescription).toBe(PHOTOS);
    expect(options("expo-camera").cameraPermission).toBe(CAMERA);
    expect(options("expo-image-picker").cameraPermission).toBe(CAMERA);
    expect(options("expo-image-picker").photosPermission).toBe(PHOTOS);
  });

  it("declares no microphone or Face ID use on iOS", () => {
    expect(app.ios.infoPlist.NSMicrophoneUsageDescription).toBe(false);
    expect(app.ios.infoPlist.NSFaceIDUsageDescription).toBe(false);
    expect(options("expo-camera").microphonePermission).toBe(false);
    expect(options("expo-image-picker").microphonePermission).toBe(false);
    expect(options("expo-secure-store").faceIDPermission).toBe(false);
  });

  it("requests no audio recording on Android", () => {
    expect(options("expo-camera").recordAudioAndroid).toBe(false);
    expect(
      (app.android.permissions ?? []).includes(
        "android.permission.RECORD_AUDIO",
      ),
    ).toBe(false);
  });
});

// w21/176: the purpose strings were set in English only, so a German prompt
// had a German title and buttons around an English body.
describe("localized purpose strings", () => {
  const languages = app.ios.infoPlist.CFBundleLocalizations as string[];
  const strings = (language: string) =>
    JSON.parse(
      fs.readFileSync(
        path.join(__dirname, "..", "..", app.locales?.[language] ?? ""),
        "utf8",
      ),
    ) as Record<string, string>;

  it("gives every bundle language its own file", () => {
    expect(Object.keys(app.locales ?? {}).sort()).toEqual(
      [...languages].sort(),
    );
  });

  it("explains the camera and photos in each of them", () => {
    for (const language of languages) {
      const { NSCameraUsageDescription, NSPhotoLibraryUsageDescription } =
        strings(language);
      expect(Boolean(NSCameraUsageDescription?.trim())).toBe(true);
      expect(Boolean(NSPhotoLibraryUsageDescription?.trim())).toBe(true);
      if (language !== "en") {
        expect(NSCameraUsageDescription === CAMERA).toBe(false);
      }
    }
    expect(strings("en").NSCameraUsageDescription).toBe(CAMERA);
    expect(strings("en").NSPhotoLibraryUsageDescription).toBe(PHOTOS);
  });
});

// w21/359: the bare `ios` pattern in .gitignore also matched locales/ios, so the
// localized strings existed only in one working tree, the camera prompt stayed
// English in builds, and this suite failed on a clean checkout.
describe("the localized iOS permission strings are tracked", () => {
  const { execFileSync } = require("child_process");
  const files = Object.values(app.locales ?? {});

  it("lists a file for each language", () => {
    expect(files.length).toBe(13);
  });

  it("none of them is ignored by git", () => {
    const ignored = files.filter((file) => {
      try {
        execFileSync("git", ["check-ignore", "-q", file], {
          cwd: path.join(__dirname, "..", ".."),
        });
        return true; // exit 0: ignored
      } catch (error) {
        return (error as { status?: number }).status !== 1;
      }
    });
    expect(ignored).toEqual([]);
  });
});
