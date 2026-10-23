import { setPendingAppLink } from "./pending-app-link";
import { resolveAppLink, HOSTED_APP_ORIGIN } from "./resolve-app-link";
import { isOAuthCallbackUrl } from "./oauth-callback-url";
import type { Href } from "expo-router";

/**
 * Pure rewrite used by `app/+native-intent.tsx`. Kept free of server-url vars
 * so unit tests can load it under jest-lite.
 */
export function rewriteSystemPath(
  path: string,
  serverUrl: string = HOSTED_APP_ORIGIN,
): string | null {
  if (isOAuthCallbackUrl(path)) {
    return path;
  }

  const url = canonicalizeIncomingAppLinkUrl(path);
  if (!url) {
    return path;
  }

  const target = resolveAppLink(url, { serverUrl });
  if (!target) {
    if (pathIncludesLedger(path)) {
      return "/";
    }
    return path;
  }

  setPendingAppLink(target, url);
  return hrefToPath(target.href);
}

/**
 * Map an incoming system path or custom-scheme URL to a hosted https ledger
 * URL the resolver understands. Returns null when the input is not a ledger
 * link (so callers leave non-ledger deep links alone).
 */
export function canonicalizeIncomingAppLinkUrl(path: string): string | null {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  // Custom-scheme links that still carry a /ledger/... path (simulator
  // verification when AASA is not yet live, or share-sheet fallbacks).
  const custom = /^[a-z][a-z0-9+.-]*:\/+(.+)$/i.exec(path);
  if (custom?.[1]) {
    const rest = custom[1].startsWith("/") ? custom[1] : `/${custom[1]}`;
    if (rest.startsWith("/ledger/")) {
      return `${HOSTED_APP_ORIGIN}${rest}`;
    }
  }
  if (path.startsWith("/ledger/") || path.startsWith("ledger/")) {
    const normalized = path.startsWith("/") ? path : `/${path}`;
    return `${HOSTED_APP_ORIGIN}${normalized}`;
  }
  return null;
}

/**
 * The hosted https URL of a `/ledger/…` link the app has no screen for: a
 * profile such as `/ledger/open_ledger`, or `/ledger` itself. Opening it in the
 * browser beats the old rewrite to Home for whatever ledger was current
 * (w21/346). Null for links the resolver maps, for anything that is not a
 * hosted ledger URL, and for foreign hosts, which are never opened from here.
 */
export function browserFallbackUrl(path: string): string | null {
  const url = canonicalizeIncomingAppLinkUrl(path);
  if (!url || !pathIncludesLedger(path)) return null;
  try {
    if (new URL(url).origin !== HOSTED_APP_ORIGIN) return null;
  } catch {
    return null;
  }
  return resolveAppLink(url) === null ? url : null;
}

function pathIncludesLedger(path: string): boolean {
  return /(?:^|\/)ledger\//.test(path) || /beancount\.io\/ledger\//i.test(path);
}

export function hrefToPath(href: Href): string {
  if (typeof href === "string") {
    return href;
  }
  if (!href || typeof href !== "object" || !("pathname" in href)) {
    return "/";
  }
  const pathname = String(href.pathname ?? "/");
  const params = (href.params ?? {}) as Record<string, string | undefined>;
  const query = Object.entries(params)
    .filter((entry): entry is [string, string] => typeof entry[1] === "string")
    .map(
      ([key, value]) =>
        `${encodeURIComponent(key)}=${encodeURIComponent(value)}`,
    )
    .join("&");
  return query ? `${pathname}?${query}` : pathname;
}
