import {
  HOSTED_APP_ORIGIN,
  normalizeOrigin,
  resolveAppLink,
  type AppLinkTarget,
} from "./resolve-app-link";
import { canonicalizeIncomingAppLinkUrl } from "./rewrite-system-path";

export type ServerLink =
  | { kind: "open"; target: AppLinkTarget; url: string }
  | { kind: "browser"; url: string }
  | { kind: "ignore" };

/**
 * What an incoming link means for the server the session is on. A custom-scheme
 * or bare-path link carries no host, so it means the selected server; an https
 * link means the server it names. A beancount.io link while another server is
 * selected is the hosted service's ledger, never the same-named one here, so it
 * goes to the browser (w21/348).
 */
export function resolveServerLink(
  incoming: string,
  serverUrl: string,
): ServerLink {
  const canonical = canonicalizeIncomingAppLinkUrl(incoming) ?? incoming;
  const named = /^https?:\/\//i.test(incoming);
  let url = canonical;
  if (!named) {
    try {
      const parsed = new URL(canonical);
      url = `${normalizeOrigin(serverUrl)}${parsed.pathname}${parsed.search}`;
    } catch {
      return { kind: "ignore" };
    }
  }
  const target = resolveAppLink(url, { serverUrl });
  if (target) return { kind: "open", target, url };
  const hosted = resolveAppLink(url, {
    serverUrl: HOSTED_APP_ORIGIN,
  });
  return hosted ? { kind: "browser", url } : { kind: "ignore" };
}
