import * as FileSystem from "expo-file-system/legacy";

/**
 * Receipt photos are full receipts (card digits, merchant, amounts, sometimes
 * names), kept by the camera and the picker in the app's cache folders. Nothing
 * removed them after an upload, a cancel or a sign-out, so they outlived the
 * account until iOS cleared the cache under storage pressure (w21/585).
 */

/** Delete one captured or picked photo. Never throws: a missing file is done. */
export function deleteReceiptShot(uri: string): Promise<void> {
  return FileSystem.deleteAsync(uri, { idempotent: true }).catch(
    () => undefined,
  );
}

/** The cache folders the camera and the image picker write receipts into. */
const RECEIPT_CACHE_FOLDERS = ["Camera/", "ImagePicker/"];

/** Empty both receipt cache folders, as sign-out must. */
export async function sweepReceiptCaches(): Promise<void> {
  const base = FileSystem.cacheDirectory;
  if (!base) return;
  await Promise.all(
    RECEIPT_CACHE_FOLDERS.map((folder) =>
      FileSystem.deleteAsync(`${base}${folder}`, { idempotent: true }).catch(
        () => undefined,
      ),
    ),
  );
}
