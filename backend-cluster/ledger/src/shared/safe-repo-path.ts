import { BadUserInputError } from "@/shared/errors";

/**
 * Guards for user-supplied repo file paths that get interpolated into Gitea
 * REST URL paths (`/repos/{owner}/{repo}/contents/{filepath}`).
 *
 * The generated client splices the string RAW into the URL template, and
 * fetch's URL parser collapses dot segments — so an un-validated
 * `../../../../user/emails` rewrites the request to a DIFFERENT API endpoint
 * (`GET /api/v1/user/emails`), and `../../other/repo/contents/x` reads another
 * repository — both executed with the caller's Gitea credential. Paths reach
 * these call sites from the dashboard, the MCP surface, and the AI agent's
 * tool arguments (i.e. prompt-injectable), so every URL-path interpolation
 * must go through {@link toSafeRepoUrlPath}.
 *
 * (Paths sent in JSON bodies — `repoChangeFiles` — are validated server-side
 * by Gitea and are not URL-parsed; validating them too is harmless and keeps
 * one rule everywhere.)
 */

/**
 * Reject a repo-relative path containing traversal / absolute / empty
 * segments, NULs, or backslashes, or one inside `.git` — Gitea refuses any
 * `.git` component, case-insensitively and at any depth, with an error the
 * listing route would otherwise report as an outage (w23/027). Throws
 * {@link BadUserInputError}.
 */
export function assertSafeRepoPath(
  path: unknown,
  field = "path",
): asserts path is string {
  if (typeof path !== "string" || path.length === 0) {
    throw new BadUserInputError("File path must not be empty", field);
  }
  if (path.includes("\0") || path.includes("\\")) {
    throw new BadUserInputError(`Invalid file path: ${path}`, field);
  }
  for (const segment of path.split("/")) {
    if (segment === "" || segment === "." || segment === "..") {
      throw new BadUserInputError(`Invalid file path: ${path}`, field);
    }
    if (segment.toLowerCase() === ".git") {
      throw new BadUserInputError(
        `Paths inside .git can't be read or written: ${path}`,
        field,
      );
    }
  }
}

/** Windows device names, with or without an extension. */
const DEVICE_NAME = /^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$/i;

/**
 * A path for a file being created: safe ({@link assertSafeRepoPath}) and
 * portable. A committed name with a control character, a bidi override, a
 * Windows-reserved character or device name, a segment ending in `.` or a
 * space, or a segment over 255 bytes made the ledger fail to clone on Windows,
 * display under another name, or resist an `include` (w23/054). Only new paths
 * are held to it, so a file already named that way stays readable and
 * deletable.
 */
export function assertPortableRepoPath(path: unknown, field = "path"): void {
  assertSafeRepoPath(path, field);
  const refuse = (rule: string) => {
    throw new BadUserInputError(
      `File path ${JSON.stringify(path)} ${rule}`,
      field,
    );
  };
  if (/[\p{Cc}\u2028\u2029]/u.test(path))
    refuse("contains a control character");
  if (/\p{Bidi_Control}/u.test(path))
    refuse("contains a bidirectional text control");
  if (/[<>:"|?*]/.test(path))
    refuse('contains one of <>:"|?*, which Windows cannot store');
  for (const segment of path.split("/")) {
    if (/[. ]$/.test(segment)) refuse("has a part ending in a dot or a space");
    if (DEVICE_NAME.test(segment))
      refuse(`uses the Windows device name "${segment}"`);
    if (Buffer.byteLength(segment, "utf8") > 255)
      refuse("has a part longer than 255 bytes");
  }
}

/**
 * Validate ({@link assertSafeRepoPath}) then URL-encode each segment, so
 * `?`/`#`/`%`/unicode in legitimate filenames reach Gitea as literals instead
 * of being interpreted by the URL parser. Use the RETURN VALUE in the client
 * call; keep the original string for maps/messages.
 */
export function toSafeRepoUrlPath(path: string, field = "path"): string {
  assertSafeRepoPath(path, field);
  return path.split("/").map(encodeURIComponent).join("/");
}
