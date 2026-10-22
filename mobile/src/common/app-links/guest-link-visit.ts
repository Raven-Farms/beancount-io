import {
  EXAMPLE_IDS,
  type ExampleId,
  type GuestView,
} from "../guest/guest-state";
import { isOfficialServerUrl } from "../server-url-validation";
import type { TransactionFilters } from "../../screens/transactions-screen/filters/types";
import type { AppLinkTarget } from "./resolve-app-link";

/**
 * The guest tabs a link can name; the app has no guest budget or reports
 * detail. Accounts and Files are guest tabs too (w21/490); a file link other
 * than the Files tab itself keeps waiting for sign-in.
 */
const GUEST_VIEWS: Record<string, GuestView> = {
  "/": "home",
  "/accounts": "accounts",
  "/transactions": "transactions",
  "/reports": "reports",
  "/ledger": "files",
};

/**
 * The guest detail screen an entry or account link opens, and the tab behind it.
 * Keyed `route`, not `pathname`, so the route-ledger scan (w2/040) sees the
 * navigation object built below, whose params carry the link's `ledger`.
 */
const GUEST_DETAILS: Record<string, { route: string; view: GuestView }> = {
  "/transaction-detail": {
    route: "/examples/transaction-detail",
    view: "transactions",
  },
  "/account-detail": { route: "/examples/account-detail", view: "accounts" },
};

/** An entry or account page of an example, as a navigation target. */
export type GuestDetail = {
  pathname: string;
  params: Record<string, string>;
};

/**
 * The guest visit a signed-out link should open: it names one of the curated
 * public examples, on the official server, and a view guests have. Anything
 * else waits for sign-in as before (w21/345).
 */
export function guestLinkVisit(
  target: AppLinkTarget,
  serverUrl: string,
): {
  ledgerId: ExampleId;
  view: GuestView;
  filters?: TransactionFilters;
  /** An entry or account page to open over `view`, in the example (w21/632). */
  detail?: GuestDetail;
} | null {
  if (!isOfficialServerUrl(serverUrl)) return null;
  if (typeof target.href !== "string") return guestDetailVisit(target);
  const ledgerId = EXAMPLE_IDS.find((id) => id === target.ledgerFullName);
  const view = GUEST_VIEWS[target.href];
  // A journal link's filters (?account=, ?time=) travel with the visit, as a
  // signed-in link's apply on open (w21/344, w21/489).
  return ledgerId && view
    ? { ledgerId, view, ...(target.filters ? { filters: target.filters } : {}) }
    : null;
}

/**
 * An entry or account link on an example: the guest has detail screens for both
 * (`/examples/transaction-detail`, `/examples/account-detail`), and the link
 * came from the guest's own Share or Copy link. It was sent to Welcome and
 * replayed after a later sign-in (w21/632).
 */
function guestDetailVisit(target: AppLinkTarget): {
  ledgerId: ExampleId;
  view: GuestView;
  detail: GuestDetail;
} | null {
  const ledgerId = EXAMPLE_IDS.find((id) => id === target.ledgerFullName);
  const href = target.href;
  if (!ledgerId || typeof href === "string" || !("pathname" in href)) {
    return null;
  }
  const kind = GUEST_DETAILS[href.pathname];
  const params = (href as { params?: Record<string, unknown> }).params ?? {};
  if (!kind) return null;
  const strings = Object.fromEntries(
    Object.entries(params).filter(
      (entry): entry is [string, string] => typeof entry[1] === "string",
    ),
  );
  return {
    ledgerId,
    view: kind.view,
    detail: { pathname: kind.route, params: strings },
  };
}
