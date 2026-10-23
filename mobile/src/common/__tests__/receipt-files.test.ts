import fs from "fs";
import path from "path";
import vm from "vm";
import ts from "typescript";

/**
 * w21/585: receipt photos stayed in the app's cache after an upload, a cancel
 * and a sign-out. Runs the real helpers with the file system stubbed.
 */
const deleted: { target: string; options: unknown }[] = [];
let failDeletes = false;
const files: Record<string, any> = {};
vm.runInNewContext(
  ts.transpileModule(
    fs.readFileSync(path.join(__dirname, "..", "receipt-files.ts"), "utf8"),
    { compilerOptions: { module: ts.ModuleKind.CommonJS } },
  ).outputText,
  {
    exports: files,
    require: (id: string) => {
      if (id !== "expo-file-system/legacy") {
        throw new Error(`Unexpected dependency ${id}`);
      }
      return {
        cacheDirectory: "file:///app/Library/Caches/",
        deleteAsync: async (target: string, options: unknown) => {
          deleted.push({ target, options });
          if (failDeletes) throw new Error("gone already");
        },
      };
    },
  },
);

beforeEach(() => {
  deleted.length = 0;
  failDeletes = false;
});

describe("receipt photo cleanup", () => {
  it("deletes a photo, and counts a missing one as done", async () => {
    await files.deleteReceiptShot("file:///app/Library/Caches/Camera/a.jpg");
    // Compared as JSON: the helper ran in another realm.
    expect(JSON.stringify(deleted)).toBe(
      JSON.stringify([
        {
          target: "file:///app/Library/Caches/Camera/a.jpg",
          options: { idempotent: true },
        },
      ]),
    );
    failDeletes = true;
    expect(await files.deleteReceiptShot("file:///x.jpg")).toBe(undefined);
  });

  it("sweeps the camera's and the picker's cache folders at sign-out", async () => {
    await files.sweepReceiptCaches();
    expect(deleted.map((entry) => entry.target).sort()).toEqual([
      "file:///app/Library/Caches/Camera/",
      "file:///app/Library/Caches/ImagePicker/",
    ]);
    failDeletes = true;
    expect(await files.sweepReceiptCaches()).toBe(undefined);
  });

  it("is part of the sign-out cleanup and of the receipt screen's exits", () => {
    const read = (...parts: string[]) =>
      fs
        .readFileSync(path.join(__dirname, "..", "..", ...parts), "utf8")
        .replace(/\s+/g, "");
    expect(
      read("common", "server-url-actions.ts").includes("sweepReceiptCaches(),"),
    ).toBe(true);
    const screen = read(
      "screens",
      "receipt-capture-screen",
      "receipt-capture-screen.tsx",
    );
    // Dropped on a retake and when the screen is left.
    expect(screen.includes("dropPhotos();setShot(null);")).toBe(true);
    expect(screen.includes("useEffect(()=>dropPhotos,[]);")).toBe(true);
    expect(screen.includes("deleteReceiptShot(uri)")).toBe(true);
  });
});
