import {
  EXAMPLE_IDS,
  type ExampleId,
  type GuestView,
} from "../guest/guest-state";
import { isOfficialServerUrl } from "../server-url-validation";
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
): { ledgerId: ExampleId; view: GuestView } | null {
  if (!isOfficialServerUrl(serverUrl) || typeof target.href !== "string") {
    return null;
  }
  const ledgerId = EXAMPLE_IDS.find((id) => id === target.ledgerFullName);
  const view = GUEST_VIEWS[target.href];
  return ledgerId && view ? { ledgerId, view } : null;
}
