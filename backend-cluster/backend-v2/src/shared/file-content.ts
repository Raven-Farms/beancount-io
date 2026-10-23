import { isUtf8 } from "buffer";
import { BadUserInputError } from "@/shared/errors";

/**
 * Fava's file-content responses carry an optional base64 `encoding` for
 * non-UTF-8-safe bytes; anything else is sent as plain text. This is the one
 * place that distinction is resolved into a plain string. `lossy` is true when
 * the bytes are not valid UTF-8, so `content` holds U+FFFD where they could not
 * be decoded and writing it back would replace bytes nobody touched (w23/030).
 */
export function decodeFileContent(file: {
  content?: string | null;
  encoding?: string | null;
}): { content: string; lossy: boolean } {
  if (!file.content) return { content: "", lossy: false };
  if (file.encoding === "base64") {
    const bytes = Buffer.from(file.content.replace(/\s/g, ""), "base64");
    return { content: bytes.toString("utf-8"), lossy: !isUtf8(bytes) };
  }
  return { content: file.content, lossy: false };
}

/**
 * Refuses to rewrite a file from its lossy text: an edit, append or include
 * rewrite re-encodes the whole file, so every undecodable byte would become
 * U+FFFD. Whole-file replacement, rename and delete never read the text.
 */
export function assertWritableText(
  file: { path: string; lossy?: boolean },
  field = "path",
): void {
  if (!file.lossy) return;
  throw new BadUserInputError(
    `${file.path} is not valid UTF-8; convert it to UTF-8 before editing it (rename and delete still work)`,
    field,
    "Re-encode the file as UTF-8 and write it whole — replace its full content, or push it with git.",
  );
}
