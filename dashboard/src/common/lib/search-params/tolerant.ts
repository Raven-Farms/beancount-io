import { z } from "zod";

/**
 * Lenient readers for search params a person types or edits. TanStack Router
 * JSON-decodes each value, so `?editMode=1`, `?next=123` and `?q=[1]` arrive
 * as numbers, booleans and arrays. A strict zod type rejects them during SSR
 * as a `SearchParamError`, which the error boundary serves as HTTP 500. These
 * read the obvious spellings and drop anything else, so the page renders its
 * default instead.
 */

/** A string; a number or boolean is read back as the text that was typed. */
export const searchString = () =>
  z
    .unknown()
    .transform((value): string | undefined =>
      typeof value === "string"
        ? value
        : typeof value === "number" || typeof value === "boolean"
          ? String(value)
          : undefined,
    )
    .optional();

const TRUE_SPELLINGS = new Set(["true", "1", "yes"]);
const FALSE_SPELLINGS = new Set(["false", "0", "no"]);

/** A flag: `true`, `1` or `yes` (and their opposites), in any case. */
export const searchBoolean = () =>
  z
    .unknown()
    .transform((value): boolean | undefined => {
      if (typeof value === "boolean") return value;
      const text = String(value).trim().toLowerCase();
      if (TRUE_SPELLINGS.has(text)) return true;
      if (FALSE_SPELLINGS.has(text)) return false;
      return undefined;
    })
    .optional();

/** A positive whole number, also when it arrives as digits in a string. */
export const searchPositiveInteger = () =>
  z
    .unknown()
    .transform((value): number | undefined => {
      const number =
        typeof value === "number"
          ? value
          : typeof value === "string" && /^\d+$/.test(value.trim())
            ? Number(value)
            : NaN;
      return Number.isSafeInteger(number) && number > 0 ? number : undefined;
    })
    .optional();

/** One of `values`, matched without regard to case. */
export const searchEnum = <const T extends readonly [string, ...string[]]>(
  values: T,
) =>
  z
    .unknown()
    .transform((value): T[number] | undefined =>
      typeof value === "string"
        ? values.find((option) => option.toLowerCase() === value.toLowerCase())
        : undefined,
    )
    .optional();
