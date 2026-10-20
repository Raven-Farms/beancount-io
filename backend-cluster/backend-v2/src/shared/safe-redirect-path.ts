/**
 * Backend twin of the dashboard's `getSafeRedirectPath`
 * (dashboard/src/common/lib/auth/auth.ts), for redirects the backend issues
 * itself (Sign in with Google). Same rules, same adversarial cases: only
 * same-origin relative paths survive; absolute and protocol-relative URLs,
 * backslash variants and control-character tricks are rejected raw or
 * percent-encoded, through several decoding layers. A hostile value is
 * rejected, never repaired. Packages stay independent (root AGENTS.md), so
 * this is a copy rather than an import.
 */

const RESOLUTION_BASE = "https://placeholder.invalid";
const MAX_DECODE_DEPTH = 4;

const hasControlCharacter = (value: string): boolean => {
  for (const character of value) {
    const code = character.codePointAt(0) ?? 0;
    if (code <= 0x1f || code === 0x7f) return true;
  }
  return false;
};

const pathOf = (value: string): string => value.split(/[?#]/, 1)[0];

const decodePercentEscapes = (value: string): string =>
  value.replace(/%([0-9a-f]{2})/gi, (_, hex: string) =>
    String.fromCharCode(Number.parseInt(hex, 16)),
  );

const decodedPathLayers = (next: string): string[] | null => {
  const layers: string[] = [];
  let path = pathOf(next);
  for (let depth = 0; depth < MAX_DECODE_DEPTH; depth += 1) {
    const decoded = decodePercentEscapes(path);
    if (decoded === path) return layers;
    path = pathOf(decoded);
    layers.push(path);
  }
  return null;
};

const leavesOrigin = (candidate: string): boolean => {
  if (!candidate.startsWith("/") || hasControlCharacter(candidate)) return true;
  if (candidate.startsWith("//") || candidate.startsWith("/\\")) return true;
  let resolved: URL;
  try {
    resolved = new URL(candidate, RESOLUTION_BASE);
  } catch {
    return true;
  }
  return (
    resolved.origin !== RESOLUTION_BASE ||
    !resolved.pathname.startsWith("/") ||
    resolved.pathname.startsWith("//")
  );
};

export const getSafeRedirectPath = (
  next: string | undefined,
): string | undefined => {
  if (!next || leavesOrigin(next)) return undefined;
  const layers = decodedPathLayers(next);
  if (layers === null || layers.some(leavesOrigin)) return undefined;
  const resolved = new URL(next, RESOLUTION_BASE);
  return `${resolved.pathname}${resolved.search}${resolved.hash}`;
};
