import { getSafeRedirectPath } from "@/common/lib/auth/auth";

const KEY = "beancount.billing.return";

/**
 * Remember where a purchase began before the browser leaves for Checkout, so
 * the confirmation can offer the way back. Only a safe same-origin path is
 * kept; anything else is dropped.
 */
export function rememberReturnPath(path: string | undefined): void {
  if (typeof window === "undefined") return;
  const safe = getSafeRedirectPath(path);
  try {
    if (safe) window.sessionStorage.setItem(KEY, safe);
    else window.sessionStorage.removeItem(KEY);
  } catch {
    // Storage can be unavailable (private mode); the confirmation then
    // offers Billing only.
  }
}

/** Read and forget the remembered path, validated again on the way out. */
export function takeReturnPath(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = window.sessionStorage.getItem(KEY);
    window.sessionStorage.removeItem(KEY);
    return getSafeRedirectPath(stored ?? undefined) ?? null;
  } catch {
    return null;
  }
}
