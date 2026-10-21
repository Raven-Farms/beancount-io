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
