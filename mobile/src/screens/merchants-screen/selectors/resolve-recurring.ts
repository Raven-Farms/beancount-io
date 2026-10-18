/**
 * Resolve detection vs. a manual override into the verdict the UI shows.
 * Override always wins; absence falls through to detection. Free of `@/`
 * imports so jest-lite can require it.
 */

import type { Cadence, RecurrenceVerdict } from "./detect-recurrence";

export type RecurringOverride = "recurring" | "notRecurring";

/**
 * What the directory / merchant view treat as "this merchant is recurring".
 * A manual mark without a detectable cadence surfaces as `irregular` when the
 * history was long enough to analyse, and as `unknown` when it was too short
 * to tell: two identical monthly payments are not irregular (w0/039).
 */
export type ResolvedCadence = Cadence | "irregular" | "unknown";

export interface ResolvedRecurring {
  isRecurring: boolean;
  /** Present when recurring — from detection, or `"irregular"`/`"unknown"` when only marked. */
  cadence: ResolvedCadence | null;
  detection: RecurrenceVerdict | null;
  /** Where the yes/no came from. */
  source: "override" | "detection" | "none";
}

export function resolveRecurringVerdict(
  detection: RecurrenceVerdict | null,
  override: RecurringOverride | null,
  /** The payee's series had enough dates to analyse (`hasEnoughHistory`). */
  enoughHistory: boolean,
): ResolvedRecurring {
  if (override === "recurring") {
    return {
      isRecurring: true,
      cadence: detection?.cadence ?? (enoughHistory ? "irregular" : "unknown"),
      detection,
      source: "override",
    };
  }
  if (override === "notRecurring") {
    return {
      isRecurring: false,
      cadence: null,
      detection,
      source: "override",
    };
  }
  if (detection) {
    return {
      isRecurring: true,
      cadence: detection.cadence,
      detection,
      source: "detection",
    };
  }
  return {
    isRecurring: false,
    cadence: null,
    detection: null,
    source: "none",
  };
}
