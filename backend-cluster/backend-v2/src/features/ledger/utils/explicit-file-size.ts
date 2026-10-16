import { BadUserInputError } from "@/shared/errors";

const MAX_EXPLICIT_FILE_BYTES = 1024 * 1024;

/** Count file bytes, independently of the transport's JSON representation. */
export function assertExplicitFileContentSize(
  content: string,
  encoding: "base64" | "utf8",
  field = "content",
): void {
  const size =
    encoding === "base64"
      ? Buffer.from(content, "base64").byteLength
      : Buffer.byteLength(content, "utf8");
  if (size > MAX_EXPLICIT_FILE_BYTES) {
    throw new BadUserInputError(
      `File content must be at most 1 MiB (${MAX_EXPLICIT_FILE_BYTES} bytes); received ${size} bytes`,
      field,
      "Upload a file no larger than 1 MiB, or split it into smaller files.",
    );
  }
}
