import Router from "@koa/router";
import { BILLING_CLIENT_ID, SUBSCRIPTION_CONFIG } from "../service/stripe";
import { customerId } from "../service/subscription-plan";
import { refreshSubscriptionPeriods } from "../operations/refresh-subscription-periods";
import { isPurchase, reportPurchase } from "../operations/report-purchase";
import type { AppConfig } from "@/config/config";
import { type AppLayers } from "@/foundation/composition";
import { logger } from "@/shared/logger";
import { registerRoute } from "@/server/rest/openapi-registry";
import {
  stripeEventExampleSchema,
  stripeWebhookSuccessResponseSchema,
  stripeWebhookErrorResponseSchema,
  stripeWebhookHealthResponseSchema,
} from "./stripe-webhook-schemas";

export function setStripeWebhookHandler(
  router: Router,
  layers: AppLayers,
  analytics: AppConfig["analytics"],
): void {
  router.post("/api-gateway/stripe/webhook", (async (ctx) => {
    const signature = ctx.request.headers["stripe-signature"] as string;
    if (!signature) {
      ctx.status = 400;
      ctx.body = { error: "No Stripe signature found" };
      return;
    }
    if (!ctx.request.rawBody) {
      ctx.status = 400;
      ctx.body = { error: "Missing request body" };
      return;
    }
    try {
      const clientId = BILLING_CLIENT_ID;
      const secret = SUBSCRIPTION_CONFIG[clientId].webhookSecret;
      if (!secret) throw new Error("Live webhook secret is not configured");
      const stripe = layers.services.stripe;
      // Never route using unverified event metadata.
      const event = stripe
        .getStripeInstance(clientId)
        .webhooks.constructEvent(ctx.request.rawBody, signature, secret);
      const object = event.data.object;
      const metadata = "metadata" in object ? object.metadata : undefined;
      if (
        !event.livemode ||
        (metadata?.clientId && metadata.clientId !== clientId)
      ) {
        ctx.status = 200;
        ctx.body = {
          received: true,
          processed: false,
          reason: "Unsupported billing client or test event",
        };
        return;
      }
      let processed = false;
      switch (event.type) {
        case "customer.subscription.created":
        case "customer.subscription.updated":
        case "customer.subscription.deleted": {
          const binding =
            await layers.database.models.paidCustomer.findByStripeCustomerIdAndClientId(
              layers.database.db,
              customerId(event.data.object.customer),
              clientId,
            );
          if (
            binding &&
            (!metadata?.userId || metadata.userId === binding.userId)
          ) {
            // Re-read all subscriptions: delayed/deleted events must not overwrite a newer renewal.
            await refreshSubscriptionPeriods(
              stripe,
              layers.database.models,
              layers.database.db,
              binding.userId,
            );
            processed = true;
          }
          break;
        }
        case "customer.created":
        case "customer.updated":
          if (metadata?.userId) {
            await stripe.handleCustomerEvent(
              event.data.object,
              event.type.replace("customer.", ""),
              event.data.previous_attributes ?? {},
              clientId,
              metadata.userId,
            );
            processed = true;
          }
          break;
        case "invoice.paid": {
          const invoice = event.data.object;
          if (!isPurchase(invoice)) break;
          // A first Checkout's invoice can arrive before the session that
          // binds the customer, so the subscription's signed metadata names
          // the user; a binding, when present, must agree.
          const subscriptionMetadata =
            invoice.parent?.subscription_details?.metadata ?? {};
          const binding = invoice.customer
            ? await layers.database.models.paidCustomer.findByStripeCustomerIdAndClientId(
                layers.database.db,
                customerId(invoice.customer),
                clientId,
              )
            : null;
          const userId = binding?.userId ?? subscriptionMetadata.userId;
          if (
            !userId ||
            (subscriptionMetadata.userId &&
              subscriptionMetadata.userId !== userId) ||
            (subscriptionMetadata.clientId &&
              subscriptionMetadata.clientId !== clientId)
          ) {
            logger.warn("Paid invoice names no matching user; not reported");
            break;
          }
          const report = await reportPurchase(
            {
              models: layers.database.models,
              db: layers.database.db,
              analytics,
              plans: SUBSCRIPTION_CONFIG[clientId].plans,
            },
            invoice,
            userId,
          );
          // Answer with an error so Stripe redelivers; the claim was given back.
          if (report === "failed") throw new Error("Purchase report failed");
          processed = report !== "unconfigured";
          break;
        }
        case "checkout.session.completed":
          if (metadata?.userId) {
            await stripe.handleCheckoutSessionCompleted(
              event.data.object,
              clientId,
              metadata.userId,
            );
            processed = true;
          }
          break;
      }
      ctx.status = 200;
      ctx.body = { received: true, processed };
    } catch (error) {
      logger.error("Error processing Stripe webhook", {
        errorType: error instanceof Error ? error.name : typeof error,
      });
      ctx.status = 400;
      ctx.body = { error: "Webhook verification or processing failed" };
    }
  }) as Router.Middleware);
  router.get("/api-gateway/stripe/webhook", (ctx) => {
    ctx.status = 200;
    ctx.body = { ok: true };
  });
  registerStripeWebhookOpenAPIRoutes();
}

/**
 * Register Stripe webhook endpoints with OpenAPI documentation
 */
function registerStripeWebhookOpenAPIRoutes() {
  // POST /api-gateway/stripe/webhook
  registerRoute({
    method: "post",
    path: "/api-gateway/stripe/webhook",
    summary: "Handle Stripe webhook events",
    description: `Receives and processes webhook events from Stripe for payment and subscription management.

**Important**: This endpoint expects raw request body for signature verification.

**Event Processing**:
- Verifies webhook signature using client-specific webhook secret
- Verifies the live client before reading metadata; resolves subscription ownership from the customer binding
- Processes customer, checkout and subscription lifecycle events
- Returns 200 even for ignored events (missing metadata) to prevent retries

**Billing client**:
Only the configured live billing client is supported; signed test events are ignored.

**Security**:
- Signature verification prevents unauthorized events
- Retired-client metadata and test events are ignored
- Subscription events refresh current Stripe state rather than replay stale cache values`,
    tags: ["Stripe Webhooks"],
    request: {
      body: {
        description: `Raw Stripe webhook event payload (JSON). Must include metadata.clientId and optionally metadata.userId.

**Required Headers**:
- 'stripe-signature': Stripe webhook signature for verification (required)
- 'stripe-event-id': Optional Stripe event ID for tracking (optional)`,
        content: {
          "application/json": {
            schema: stripeEventExampleSchema,
          },
        },
      },
    },
    responses: {
      200: {
        description: "Webhook received and processed (or acknowledged)",
        content: {
          "application/json": {
            schema: stripeWebhookSuccessResponseSchema,
          },
        },
      },
      400: {
        description:
          "Invalid signature, missing body, or webhook processing error",
        content: {
          "application/json": {
            schema: stripeWebhookErrorResponseSchema,
          },
        },
      },
    },
  });

  // GET /api-gateway/stripe/webhook
  registerRoute({
    method: "get",
    path: "/api-gateway/stripe/webhook",
    summary: "Stripe webhook health check",
    description:
      "Simple health check endpoint to verify the webhook endpoint is accessible. Used by Stripe and monitoring systems.",
    tags: ["Stripe Webhooks"],
    responses: {
      200: {
        description: "Webhook endpoint is healthy",
        content: {
          "application/json": {
            schema: stripeWebhookHealthResponseSchema,
          },
        },
      },
    },
  });
}
