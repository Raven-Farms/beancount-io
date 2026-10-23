/**
 * A saved list of strings, read back from browser storage.
 *
 * Saved preferences are browser data, not ours: valid JSON of the wrong
 * shape crashed the pages that spread or `.includes` it (w4/m39). A value
 * that is not a list throws, so `useLocalStorageState` falls back to its
 * default on mount and keeps the last good value on a cross-tab update.
 * Members that are not strings, or that `accept` refuses, are dropped.
 */
export function decodeStringList<T extends string = string>(
  raw: string,
  accept: (value: string) => value is T = (_value): _value is T => true,
): T[] {
  const value: unknown = JSON.parse(raw);
  if (!Array.isArray(value)) {
    throw new TypeError("saved value is not a list");
  }
  return value.filter(
    (item): item is T => typeof item === "string" && accept(item),
  );
}
