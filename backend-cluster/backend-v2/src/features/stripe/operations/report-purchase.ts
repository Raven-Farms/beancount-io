import { createHash } from "node:crypto";
import type Stripe from "stripe";
import type { AppConfig } from "@/config/config";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { IModels } from "@/foundation/models";
import { logger } from "@/shared/logger";
import type { PlanConfig } from "../service/stripe";

const reportLogger = logger.child({ module: "report-purchase" });

const COLLECT_URL = "https://www.google-analytics.com/mp/collect";
const SEND_TIMEOUT_MS = 5_000;

/**
 * The invoices that are a purchase: a Checkout's first invoice and the
 * proration an immediate plan change charges. Renewals are not new purchases.
 */
const PURCHASE_REASONS: ReadonlySet<Stripe.Invoice.BillingReason> = new Set([
  "subscription_create",
  "subscription_update",
]);

export type PurchaseReport =
  | "reported"
  | "unconfigured"
  | "already_reported"
  | "failed";

export interface ReportPurchaseDeps {
  models: Pick<IModels, "reportedPurchase">;
  db: DbExecutor;
  analytics: AppConfig["analytics"];
  plans: readonly PlanConfig[];
  fetch?: typeof fetch;
}

/** A paid invoice that is a purchase; a fully discounted one is not revenue. */
export function isPurchase(
  invoice: Stripe.Invoice,
): invoice is Stripe.Invoice & { id: string } {
  return (
    !!invoice.id &&
    !!invoice.billing_reason &&
    PURCHASE_REASONS.has(invoice.billing_reason) &&
    invoice.amount_paid > 0
  );
}

/** Stripe amounts are in the currency's minor unit; GA4 wants major units. */
function majorUnits(amount: number, currency: string): number {
  const digits =
    new Intl.NumberFormat("en", {
      style: "currency",
      currency,
    }).resolvedOptions().maximumFractionDigits ?? 2;
  return amount / 10 ** digits;
}

/** GA4 Measurement Protocol body for a purchase invoice. */
export function purchasePayload(
  invoice: Stripe.Invoice & { id: string },
  userId: string,
  plans: readonly PlanConfig[],
) {
  const currency = invoice.currency.toUpperCase();
  // A plan invoice has one or two lines, well inside the webhook's first page.
  const items = invoice.lines.data.flatMap((line) => {
    const price = line.pricing?.price_details?.price;
    const priceId = typeof price === "string" ? price : price?.id;
    const plan = plans.find((candidate) => candidate.priceId === priceId);
    // The credit for the old plan is negative; the item is what was bought.
    if (!plan || line.amount <= 0) return [];
    return [
      {
        item_id: plan.priceId,
        item_name: plan.tier,
        item_variant: plan.interval,
        price: majorUnits(line.amount, currency),
        quantity: 1,
      },
    ];
  });
  return {
    // GA4 requires a client id; the server has none, so it derives a stable
    // one. `user_id` is what joins the event to the dashboard's journey.
    client_id: `server.${createHash("sha256").update(userId).digest("hex").slice(0, 20)}`,
    user_id: userId,
    events: [
      {
        name: "purchase",
        params: {
          transaction_id: invoice.id,
          value: majorUnits(invoice.amount_paid, currency),
          currency,
          billing_reason: invoice.billing_reason,
          items,
        },
      },
    ],
  };
}

/**
 * Report a purchase invoice to GA4 as one `purchase`. The invoice is claimed
 * before sending, so concurrent and retried deliveries send it once; a failed
 * send gives the claim back and returns "failed" so the webhook can ask
 * Stripe to retry. A claim the database cannot record throws, for the same
 * reason.
 */
export async function reportPurchase(
  deps: ReportPurchaseDeps,
  invoice: Stripe.Invoice & { id: string },
  userId: string,
): Promise<PurchaseReport> {
  const { gaMeasurementId, measurementProtocolSecret } = deps.analytics;
  if (!gaMeasurementId || !measurementProtocolSecret) return "unconfigured";
  if (!(await deps.models.reportedPurchase.claim(deps.db, invoice.id))) {
    return "already_reported";
  }
  try {
    const url = new URL(COLLECT_URL);
    url.searchParams.set("measurement_id", gaMeasurementId);
    url.searchParams.set("api_secret", measurementProtocolSecret);
    const response = await (deps.fetch ?? fetch)(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(purchasePayload(invoice, userId, deps.plans)),
      signal: AbortSignal.timeout(SEND_TIMEOUT_MS),
    });
    await response.body?.cancel();
    if (response.ok) return "reported";
    reportLogger.warn("GA4 rejected a purchase", { status: response.status });
  } catch (error) {
    // The URL carries the API secret, so only the error's kind is logged.
    reportLogger.warn("Could not report a purchase", {
      errorType: error instanceof Error ? error.name : typeof error,
    });
  }
  await deps.models.reportedPurchase.release(deps.db, invoice.id);
  return "failed";
}
