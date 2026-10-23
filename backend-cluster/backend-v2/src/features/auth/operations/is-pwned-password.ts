import { createHash } from "node:crypto";
import { logger } from "@/shared/logger";

const pwnedLogger = logger.child({ module: "is-pwned-password" });

const RANGE_URL = "https://api.pwnedpasswords.com/range/";
/** Sign-up and reset wait on it, so one short try. */
const LOOKUP_TIMEOUT_MS = 2_000;

export type IsPwnedPassword = (password: string) => Promise<boolean>;

/**
 * Whether Pwned Passwords lists `password` in any breach (Kratos's
 * `max_breaches: 0`), by k-anonymity: only the first five hex characters of
 * its SHA-1 leave the service, and the match is made here. `Add-Padding` adds
 * zero-count decoys so the range's size says nothing either. Like Kratos's
 * `ignore_network_errors`, an unreachable service answers `false` rather than
 * block sign-up on a third party. Not cached: sign-ups are too rare to reuse
 * any of the million ranges.
 */
export async function isPwnedPassword(
  password: string,
  deps: { fetch?: typeof fetch } = {},
): Promise<boolean> {
  const hash = createHash("sha1").update(password).digest("hex").toUpperCase();
  try {
    const response = await (deps.fetch ?? fetch)(RANGE_URL + hash.slice(0, 5), {
      headers: { "Add-Padding": "true", "User-Agent": "beancount.io" },
      signal: AbortSignal.timeout(LOOKUP_TIMEOUT_MS),
    });
    if (!response.ok) {
      await response.body?.cancel();
      pwnedLogger.warn("Pwned Passwords refused a range lookup", {
        status: response.status,
      });
      return false;
    }
    const match = new RegExp(`^${hash.slice(5)}:(\\d+)`, "im").exec(
      await response.text(),
    );
    return Number(match?.[1] ?? 0) > 0;
  } catch (error) {
    // Nothing about the password, its hash or its prefix is logged.
    pwnedLogger.warn("Could not reach Pwned Passwords", {
      errorType: error instanceof Error ? error.name : typeof error,
    });
    return false;
  }
}
