/**
 * Document-level navigation for destinations outside this SPA router —
 * cross-app pages like the marketing site's /pricing, which the dashboard's
 * route tree cannot resolve (the router would 404 at the catch-all) — and for
 * in-app pages that must not inherit the router's loaded state, such as login
 * after a password reset ended the current session.
 *
 * Also a test seam: jsdom marks `window.location` unforgeable, so call sites
 * that invoke `window.location.assign` directly cannot be unit-tested.
 */
export function hardNavigate(href: string): void {
  window.location.assign(href);
}
