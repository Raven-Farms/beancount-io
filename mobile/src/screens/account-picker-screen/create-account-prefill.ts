/**
 * Turkish dotless i: its uppercase "I" is a different letter in Turkish, so it
 * is left as typed, as the dotted capital İ is.
 */
const DOTLESS_I = "\u0131";

/**
 * The account name the picker's "Create" row hands to Open Account.
 *
 * Search is case-insensitive, so people type `groceries`, but Open Account
 * requires each component to start with an uppercase letter or a digit, so the
 * raw query opened a form that was already invalid. Each component's first
 * character is capitalized when it is a lowercase letter, in any cased script
 * (Latin, Cyrillic, Greek, …), with a single-character uppercase form (w21/260).
 * Caseless scripts (Han, Kana, …), digits,
 * and everything after the first character pass through as typed, so a name
 * that is invalid for another reason still shows its own error on the form.
 */
export function capitalizeAccountPrefill(query: string): string {
  if (query.trim() === "") return query;
  return query
    .split(":")
    .map((raw) => {
      // A space after the colon ("expenses: food") is not part of the name.
      const component = raw.trim();
      const [initial, ...rest] = [...component];
      if (initial === undefined || initial === DOTLESS_I) return component;
      const upper = initial.toUpperCase();
      // Only a cased letter changes (digits and Han, Kana, ... have no case),
      // and only to a single character (ß becomes SS, which it does not).
      if (upper === initial || [...upper].length !== 1) return component;
      return upper + rest.join("");
    })
    .join(":");
}
