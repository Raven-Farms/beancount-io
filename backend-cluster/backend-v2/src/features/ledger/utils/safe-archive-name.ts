import { BadUserInputError } from "@/shared/errors";

/** One safe URL-path segment covering every supported archive format. */
export const SAFE_ARCHIVE_NAME_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$/;

/** The formats the resource description and v1 parameter document. */
const ARCHIVE_FORMAT_PATTERN = /^(.+)\.(zip|tar\.gz)$/;

export function assertSafeArchiveName(
  archive: unknown,
): asserts archive is string {
  if (typeof archive !== "string" || !SAFE_ARCHIVE_NAME_PATTERN.test(archive)) {
    throw new BadUserInputError("Invalid archive name", "archive");
  }
  // Without a known suffix the repository host refuses the request, and that
  // refusal used to surface as "dependency down" (w23/003).
  if (!ARCHIVE_FORMAT_PATTERN.test(archive)) {
    throw new BadUserInputError(
      "Archive name must be a branch, tag or commit followed by .zip or .tar.gz",
      "archive",
      "Name the archive like `main.zip` or `main.tar.gz`.",
    );
  }
}

/** The branch, tag or commit an archive name selects. */
export function archiveRef(archive: string): string {
  return ARCHIVE_FORMAT_PATTERN.exec(archive)?.[1] ?? archive;
}
