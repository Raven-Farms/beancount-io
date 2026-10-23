import type { DbExecutor } from "@/drizzle/drizzle";
import type { IModels } from "@/foundation/models";
import type { ISendGrid } from "@/foundation/sendgrid";
import { TIER_DISPLAY_NAMES, type PlanConfig } from "../service/stripe";
import { majorUnits } from "./minor-units";

export interface BillingEmailDeps {
  models: Pick<IModels, "user" | "sentBillingEmail">;
  db: DbExecutor;
  sendgrid: ISendGrid;
}

/** What sending a billing email came to; `not-applicable` means none was due. */
export type BillingEmailOutcome =
  | "sent"
  | "already-sent"
  | "no-recipient"
  | "not-applicable";

export interface BillingMail {
  subject: string;
  html: string;
  text: string;
}

/** "Premium · Yearly" */
export function planName(plan: PlanConfig): string {
  return `${TIER_DISPLAY_NAMES[plan.tier]} · ${plan.interval === "year" ? "Yearly" : "Monthly"}`;
}

/** "October 17, 2027"; billing dates are UTC instants. */
export function longDate(at: Date): string {
  return at.toLocaleDateString("en-US", { dateStyle: "long", timeZone: "UTC" });
}

/** A Stripe amount, in the currency's minor unit, as "$143.88". */
export function money(amount: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency.toUpperCase(),
  }).format(majorUnits(amount, currency));
}

/**
 * Send a billing email to the user once per `key`. The mail is rendered
 * before claiming, so nothing that can throw sits between the claim and the
 * send; a failed send gives the claim back and rethrows, so a retry (Stripe
 * redelivering the webhook) can send it.
 */
export async function sendBillingEmailOnce(
  deps: BillingEmailDeps,
  userId: string,
  key: string,
  mail: BillingMail,
): Promise<Exclude<BillingEmailOutcome, "not-applicable">> {
  const user = await deps.models.user.getById(deps.db, userId);
  if (!user?.email) return "no-recipient";
  if (!(await deps.models.sentBillingEmail.claim(deps.db, key))) {
    return "already-sent";
  }
  try {
    await deps.sendgrid.sendMail({ to: user.email, ...mail });
  } catch (error) {
    await deps.models.sentBillingEmail.release(deps.db, key);
    throw error;
  }
  return "sent";
}
