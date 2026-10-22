import {
  EXAMPLE_IDS,
  type ExampleId,
  type GuestView,
} from "../guest/guest-state";
import { isOfficialServerUrl } from "../server-url-validation";
import type { TransactionFilters } from "../../screens/transactions-screen/filters/types";
import type { AppLinkTarget } from "./resolve-app-link";

/** The guest tabs a link can name: the app has no guest budget or reports detail. */
const GUEST_VIEWS: Record<string, GuestView> = {
  "/": "home",
  "/transactions": "transactions",
  "/reports": "reports",
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
} | null {
  if (!isOfficialServerUrl(serverUrl) || typeof target.href !== "string") {
    return null;
  }
  const ledgerId = EXAMPLE_IDS.find((id) => id === target.ledgerFullName);
  const view = GUEST_VIEWS[target.href];
  // A journal link's filters (?account=, ?time=) travel with the visit, as a
  // signed-in link's apply on open (w21/344, w21/489).
  return ledgerId && view
    ? { ledgerId, view, ...(target.filters ? { filters: target.filters } : {}) }
    : null;
}
