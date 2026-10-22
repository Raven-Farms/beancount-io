import { routeText } from "../route-text";
import { Href } from "expo-router";
import type { TransactionFilters } from "../../screens/transactions-screen/filters/types";
import { journalLinkFilters } from "./journal-link-filters";

/** Hosted production origin — always accepted by the resolver. */
export const HOSTED_APP_ORIGIN = "https://beancount.io";

export type AppLinkTarget = {
  ledgerFullName: string;
  href: Href;
  /** Transactions filters the link sets; absent for every other target. */
  filters?: TransactionFilters;
};

export type ResolveAppLinkOptions = {
  /** Selected server origin (with or without trailing slash). */
  serverUrl?: string;
  /** The hosted origin, accepted when no server is selected. Defaults to beancount.io. */
  hostedOrigin?: string;
};

export function normalizeOrigin(url: string): string {
  return url.replace(/\/+$/, "");
}

function hostFromOrigin(origin: string): string | null {
  try {
    return new URL(origin).hostname.toLowerCase();
  } catch {
    return null;
  }
}

/**
 * The hosts whose links are this server's. With a self-hosted server selected,
 * a beancount.io link names the hosted service's ledger, not the same-named
 * one on this server, so only the server's own host counts (w21/348); the
 * hosted origin is accepted when it is the server, or none is given.
 */
function allowedHosts(options: ResolveAppLinkOptions): Set<string> {
  const hosts = new Set<string>();
  const serverHost = options.serverUrl
    ? hostFromOrigin(normalizeOrigin(options.serverUrl))
    : null;
  if (serverHost) {
    hosts.add(serverHost);
  } else {
    const hostedHost = hostFromOrigin(
      normalizeOrigin(options.hostedOrigin ?? HOSTED_APP_ORIGIN),
    );
    if (hostedHost) hosts.add(hostedHost);
  }
  return hosts;
}

/**
 * Map a dashboard ledger URL to an Expo Router href + ledger identity.
 * Returns null for foreign hosts and non-ledger paths (gallery, settings, auth).
 */
export function resolveAppLink(
  url: string,
  options: ResolveAppLinkOptions = {},
): AppLinkTarget | null {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    return null;
  }

  const host = parsed.hostname.toLowerCase();
  if (!allowedHosts(options).has(host)) {
    return null;
  }

  const segments = parsed.pathname
    .replace(/\/+$/, "")
    .split("/")
    .filter(Boolean)
    .map((segment) => {
      try {
        return decodeURIComponent(segment);
      } catch {
        return segment;
      }
    });

  if (segments[0] !== "ledger" || segments.length < 3) {
    return null;
  }

  const owner = segments[1];
  const name = segments[2];
  if (!owner || !name) {
    return null;
  }

  const ledgerFullName = `${owner}/${name}`;
  const rest = segments.slice(3);

  // Prefer public pathnames (no group segments). NativeTabs + Universal Links
  // cold-start reliably honor `/reports` etc.; `/(app)/(tabs)/reports` can lose
  // the race against the tabs initial route and leave the user on Home.
  if (rest.length === 0 || (rest.length === 1 && rest[0] === "overview")) {
    return { ledgerFullName, href: "/" };
  }

  const [head, ...tail] = rest;

  switch (head) {
    case "account": {
      if (tail.length !== 1 || !tail[0]) {
        return { ledgerFullName, href: "/" };
      }
      return {
        ledgerFullName,
        href: {
          pathname: "/account-detail",
          // `ledger` binds the entry to the link's ledger: `openAppLinkTarget`
          // replaces only the current history entry, so without it a Back tap
          // could revive this account under whatever ledger is selected then.
          params: { account: tail[0], ledger: ledgerFullName },
        },
      };
    }
    case "accounts":
      return {
        ledgerFullName,
        href:
          parsed.searchParams.get("action") === "open-account"
            ? "/open-account"
            : "/accounts",
      };
    case "journal": {
      // The dashboard's "new entry" link opens its form; here, the native one.
      if (parsed.searchParams.get("action") === "new-entry") {
        const directive = parsed.searchParams.get("directive");
        if (directive === null || directive === "transaction") {
          return { ledgerFullName, href: "/add-transaction" };
        }
        if (directive === "account") {
          return { ledgerFullName, href: "/open-account" };
        }
      }
      return {
        ledgerFullName,
        href: "/transactions",
        filters: journalLinkFilters(parsed.searchParams),
      };
    }
    case "commit": {
      if (tail.length !== 1 || !tail[0]) {
        return { ledgerFullName, href: "/" };
      }
      return {
        ledgerFullName,
        href: {
          pathname: "/commit-detail",
          // `ledger` binds the commit to the link's repository (see account).
          params: { sha: tail[0], ledger: ledgerFullName },
        },
      };
    }
    case "files": {
      // /files/tree/main[/dir...] — the Files tab; it has no folder deep link,
      // so a folder opens at the root. Other branches are no app link, as for
      // a file (below).
      if (tail.length === 0 || tail[0] === "tree") {
        if (tail.length > 1 && tail[1] !== "main") return null;
        return { ledgerFullName, href: "/ledger" };
      }
      // /files/blob/$branch/$path... — mobile editor takes the path only.
      if (tail[0] !== "blob" || tail.length < 3) {
        return { ledgerFullName, href: "/" };
      }
      const path = tail.slice(2).join("/");
      if (!path) {
        return { ledgerFullName, href: "/" };
      }
      // The editor reads and writes main only. The dashboard 404s any other
      // branch rather than show main's file under a URL naming another, so the
      // link is no app link and opens in the browser (w21/347).
      if (tail[1] !== "main") return null;
      // A positive whole number only; anything else opens at the top.
      const lineNumber = parsed.searchParams.get("lineNumber") ?? "";
      const initialLine = /^[1-9]\d{0,8}$/.test(lineNumber)
        ? lineNumber
        : undefined;
      return {
        ledgerFullName,
        href: {
          pathname: "/ledger-file-editor",
          // `ledger` binds the file to the link's ledger: without it the
          // editor opened the *selected* ledger's same-named file, editable,
          // for a link to a ledger the user cannot read (w21/199).
          params: {
            path: routeText(path),
            ledger: ledgerFullName,
            // The dashboard's ledger-errors table links to the error's line.
            ...(initialLine ? { initialLine } : {}),
          },
        },
      };
    }
    case "income-statement":
    case "balance-sheet":
      return { ledgerFullName, href: "/reports" };
    case "budget":
      return { ledgerFullName, href: "/budget" };
    case "entry": {
      if (tail.length !== 1 || !tail[0]) {
        return { ledgerFullName, href: "/" };
      }
      return {
        ledgerFullName,
        href: {
          pathname: "/transaction-detail",
          // `ledger` binds the entry to the link's ledger (see account above).
          params: { entry_hash: tail[0], ledger: ledgerFullName },
        },
      };
    }
    default:
      return { ledgerFullName, href: "/" };
  }
}
