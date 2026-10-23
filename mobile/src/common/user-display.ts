export type UserIdentity = {
  email: string;
  firstName?: string | null;
  lastName?: string | null;
  username?: string | null;
};

/** The name a person recognizes as theirs: their full name, else their
 * username, else the part of their email before the `@`. */
export function userDisplayName(user: UserIdentity): string {
  const fullName = [user.firstName, user.lastName]
    .map((part) => part?.trim())
    .filter(Boolean)
    .join(" ");
  return fullName || user.username?.trim() || user.email.split("@")[0];
}

/** What extends a character within one grapheme: a mark, an emoji
 * presentation selector, or a skin tone. */
const EXTEND = "[\\p{M}\\u{FE0F}\\u{1F3FB}-\\u{1F3FF}]";
/** An Indic virama that joins the next consonant into one conjunct ("क्ष"). */
const LINKED = "[\\u094D\\u09CD\\u0ACD\\u0B4D\\u0C4D\\u0D4D]\\p{L}";
const CLUSTER = `.(?:${LINKED}|${EXTEND})*`;
/** A flag (two regional indicators), or a character with what extends it,
 * through any zero-width-joined parts ("👩‍💻"). */
const FIRST_GRAPHEME = new RegExp(
  `^(?:[\\u{1F1E6}-\\u{1F1FF}]{2}|${CLUSTER}(?:\\u200D${CLUSTER})*)`,
  "u",
);

/**
 * A word's first user-perceived character, capitalized (w21/645). One code
 * point showed half of "🇩🇪", dropped the joined half of "👩‍💻" and the skin
 * tone of "👍🏽", and lost "दी"'s vowel sign. NFKC folds a ligature ("ﬁ") and
 * composes a decomposed "Ö"; upper-casing can expand ("ﬁ" → "FI"), so the
 * first character is taken again.
 */
function initial(word: string): string {
  const first = (text: string) => FIRST_GRAPHEME.exec(text)?.[0] ?? text;
  return first(first(word.normalize("NFKC")).toUpperCase());
}

/** Up to two letters for an avatar placeholder: first and last word of the
 * name, or the first character alone for single-word and CJK names. */
export function userInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  const first = initial(words[0]);
  if (words.length === 1) return first;
  return `${first}${initial(words[words.length - 1])}`;
}

/** Gravatar serves a generic logo for addresses without a picture; `d=404`
 * makes it fail instead so the avatar can fall back to initials. The size is
 * requested in device pixels so the image stays sharp at the drawn size. */
export function avatarImageUri(
  url: string | null | undefined,
  pixelSize: number,
): string | undefined {
  if (!url) return undefined;
  const absolute = url.startsWith("//") ? `https:${url}` : url;
  if (!isGravatarUrl(absolute)) return absolute;
  // String surgery rather than `URL`: React Native's URL has no searchParams.
  const [base, query = ""] = absolute.split("?");
  const kept = query
    .split("&")
    .filter((pair) => pair && !/^(size|s|d|default)=/.test(pair));
  return `${base}?${[...kept, `s=${Math.round(pixelSize)}`, "d=404"].join("&")}`;
}

/**
 * Whether the server answers that there is no image at `uri` (a 404, which is
 * what a Gravatar `d=404` says for someone without one). Any other outcome — no
 * connection, a timeout, a server error — leaves it unknown, and unknown is
 * not "missing" (w21/430).
 */
export async function imageIsMissing(
  uri: string,
  request: typeof fetch = fetch,
): Promise<boolean> {
  try {
    return (await request(uri, { method: "HEAD" })).status === 404;
  } catch {
    return false;
  }
}

export function isGravatarUrl(url: string | null | undefined): boolean {
  return /^(https?:)?\/\/([a-z0-9-]+\.)?gravatar\.com\//i.test(url ?? "");
}
