const IMAGE_MIME_TYPES: Record<string, string> = {
  svg: "image/svg+xml",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  gif: "image/gif",
  webp: "image/webp",
  bmp: "image/bmp",
};

/** The image MIME type a ledger file's extension names, if it is an image. */
export function imageMimeType(filename: string): string | undefined {
  const dot = filename.lastIndexOf(".");
  if (dot < 0 || dot < filename.lastIndexOf("/")) return undefined;
  return IMAGE_MIME_TYPES[filename.slice(dot + 1).toLowerCase()];
}
