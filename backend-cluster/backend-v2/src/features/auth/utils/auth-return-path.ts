import { BadUserInputError } from "@/shared/errors";

const BASE = "https://placeholder.invalid";
const MAX_LENGTH = 2048;
const MAX_DECODE_DEPTH = 4;
const pathOf = (value: string): string => value.split(/[?#]/, 1)[0];

function hasControlCharacter(value: string): boolean {
  for (const character of value) {
    const code = character.codePointAt(0) ?? 0;
    if (code <= 0x1f || code === 0x7f) return true;
  }
  return false;
}

function isLocal(value: string): boolean {
  const path = pathOf(value);
  if (
    !path.startsWith("/") ||
    path.startsWith("//") ||
    path.includes("\\") ||
    hasControlCharacter(value)
  )
    return false;
  try {
    const resolved = new URL(value, BASE);
    return resolved.origin === BASE && !resolved.pathname.startsWith("//");
  } catch {
    return false;
  }
}

/** A local continuation, checked through further path-decoding layers. Query
 * values stay encoded: a BQL query can legitimately contain %0A or %5C. */
export function validateAuthReturnPath(value?: string): string | undefined {
  if (value === undefined || value === "") return undefined;
  const invalid = () =>
    new BadUserInputError(
      "Return path must be a local relative path of at most 2048 characters",
    );
  if (typeof value !== "string" || value.length > MAX_LENGTH || !isLocal(value))
    throw invalid();

  let path = pathOf(value);
  for (let depth = 0; depth < MAX_DECODE_DEPTH; depth++) {
    // Decode well-formed ASCII escapes even when a different escape is
    // malformed; decodeURIComponent would throw and miss the dangerous one.
    const decoded = path.replace(/%([0-9a-f]{2})/gi, (_, hex: string) =>
      String.fromCharCode(Number.parseInt(hex, 16)),
    );
    if (decoded === path) {
      const resolved = new URL(value, BASE);
      const result = `${resolved.pathname}${resolved.search}${resolved.hash}`;
      if (result.length > MAX_LENGTH) throw invalid();
      return result;
    }
    path = pathOf(decoded);
    if (!isLocal(path)) throw invalid();
  }
  throw invalid();
}
