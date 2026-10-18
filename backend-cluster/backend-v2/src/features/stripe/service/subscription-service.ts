import { refreshSubscriptionPeriods } from "../operations/refresh-subscription-periods";
import {
  subscriptionTier,
  SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
} from "./subscription-plan";
import type Stripe from "stripe";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { IModels } from "@/foundation/models";
import type { Identity } from "@/server/api/identity";
import {
  AUTHORIZATION_ACTIONS,
  type AuthorizationAction,
  type IAuthorizationService,
  userResource,
} from "@/server/api/authorization";
import { logger } from "@/shared/logger";
import {
  BILLING_CLIENT_ID,
  SUBSCRIPTION_CONFIG,
  TIER_LIMITS,
  SubscriptionTier,
} from "./stripe";
import type { IStripeService } from "./stripe-service";
import type {
  PaymentMethodSummaryView,
  PlanChangePreviewView,
} from "../operations/plan-change-preview";

interface SubscriptionPriceView {
  id: string;
  amount: number;
  currency: string;
  interval: string;
  intervalCount?: number;
  trialPeriodDays?: number;
}

interface SubscriptionProductView {
  id: string;
  name: string;
  description?: string;
  images?: string[];
}

interface SubscriptionItemView {
  id: string;
  price: SubscriptionPriceView;
  product?: SubscriptionProductView;
  quantity: number;
}

interface SubscriptionView {
  id: string;
  status: string;
  currentPeriodStart: Date;
  currentPeriodEnd: Date;
  clientId: string;
  cancelAt?: Date;
  canceledAt?: Date;
  cancelAtPeriodEnd: boolean;
  items: SubscriptionItemView[];
  paymentMethod: PaymentMethodSummaryView | null;
}

export interface CustomerSubscriptionStatusView {
  hasActiveSubscription: boolean;
  subscriptions: SubscriptionView[];
}

export interface SubscriptionActionResultView {
  success: boolean;
  message?: string;
}

export interface UpgradeSubscriptionResultView extends SubscriptionActionResultView {
  clientSecret?: string;
  subscriptionId?: string;
  newTier?: string;
}

export interface SubscriptionSessionResultView extends SubscriptionActionResultView {
  sessionId?: string;
  sessionUrl?: string;
}

export interface TierQuotaView {
  tier: string;
  aiCfoTokensMax: number;
  maxLedgers: number;
  maxCollaboratorsPerLedger: number;
  maxDirectives: number;
}

export interface ISubscriptionService {
  allTierQuotas(): Promise<TierQuotaView[]>;
  subscriptionStatus(
    identity: Identity,
    onlyActiveStatus: boolean,
  ): Promise<CustomerSubscriptionStatusView>;
  createSubscriptionSession(
    identity: Identity,
    clientId: string,
    priceId: string,
  ): Promise<SubscriptionSessionResultView>;
  createStripePortalSession(
    identity: Identity,
    clientId: string,
  ): Promise<SubscriptionSessionResultView>;
  cancelSubscription(
    identity: Identity,
    subscriptionId: string,
    clientId: string,
  ): Promise<SubscriptionActionResultView>;
  resumeSubscription(
    identity: Identity,
    subscriptionId: string,
    clientId: string,
  ): Promise<SubscriptionActionResultView>;
  upgradeSubscription(
    identity: Identity,
    clientId: string,
    priceId: string,
  ): Promise<UpgradeSubscriptionResultView>;
  previewPlanChange(
    identity: Identity,
    clientId: string,
    priceId: string,
  ): Promise<PlanChangePreviewView>;
}

/**
 * The application boundary for self-service billing.
 *
 * Protected methods make one final PDP decision before reading local billing
 * state or reaching Stripe. The static tier-quota catalog is deliberately
 * public. Stripe customer ownership, product allowlists, and subscription-state
 * validation remain payment-domain invariants downstream.
 */
export class SubscriptionService implements ISubscriptionService {
  constructor(
    private readonly stripe: IStripeService,
    private readonly models: Pick<IModels, "paidCustomer" | "user">,
    private readonly db: DbExecutor,
    private readonly authorization: IAuthorizationService,
  ) {}

  private async authorize(
    identity: Identity,
    action: AuthorizationAction,
  ): Promise<void> {
    await this.authorization.authorizeOrThrow({
      principal: identity,
      action,
      resource: userResource(identity.userId),
    });
  }

  public async allTierQuotas(): Promise<TierQuotaView[]> {
    return (Object.keys(TIER_LIMITS) as SubscriptionTier[]).map((tier) => ({
      tier,
      ...TIER_LIMITS[tier],
    }));
  }

  public async subscriptionStatus(
    identity: Identity,
    onlyActiveStatus: boolean,
  ): Promise<CustomerSubscriptionStatusView> {
    await this.authorize(
      identity,
      AUTHORIZATION_ACTIONS.USER_BILLING_STATUS_READ,
    );
    const { userId } = identity;

    if (onlyActiveStatus) {
      const cached =
        await this.models.paidCustomer.findByUserIdWithActivePeriod(
          this.db,
          userId,
        );
      if (
        cached?.userId === userId &&
        cached.clientId === BILLING_CLIENT_ID &&
        cached.stripeCustomerId &&
        cached.periodVerificationVersion ===
          SUBSCRIPTION_PERIOD_VERIFICATION_VERSION &&
        cached.currentPeriodEnd &&
        cached.currentPeriodEnd.getTime() > Date.now()
      ) {
        return { hasActiveSubscription: true, subscriptions: [] };
      }
    }

    const stripeSubscriptions = await refreshSubscriptionPeriods(
      this.stripe,
      this.models,
      this.db,
      userId,
      onlyActiveStatus ? "active" : "all",
    );
    const filteredSubscriptions = stripeSubscriptions.filter(
      (subscription) =>
        !!SUBSCRIPTION_CONFIG[subscription.clientId] &&
        subscription.livemode &&
        subscription.items.data.some((item) =>
          SUBSCRIPTION_CONFIG[subscription.clientId].planIds.includes(
            item.price.id,
          ),
        ),
    );
    const hasActiveSubscription = filteredSubscriptions.some(
      (subscription) =>
        subscriptionTier(subscription) !== SubscriptionTier.FREE,
    );
    if (onlyActiveStatus) return { hasActiveSubscription, subscriptions: [] };

    const products = new Map<
      string,
      Promise<Stripe.Product | Stripe.DeletedProduct>
    >();
    const loadProduct = (clientId: string, productId: string) => {
      const key = `${clientId}:${productId}`;
      let pending = products.get(key);
      if (!pending) {
        pending = this.stripe
          .getStripeInstance(clientId)
          .products.retrieve(productId);
        products.set(key, pending);
      }
      return pending;
    };
    const subscriptionsResults = await Promise.allSettled(
      filteredSubscriptions.map(async (subscription) => {
        const itemsResults = await Promise.allSettled(
          subscription.items.data.map(async (item) => {
            const { price } = item;
            const productDetails: Stripe.Product | Stripe.DeletedProduct =
              typeof price.product !== "string"
                ? price.product
                : await loadProduct(subscription.clientId, price.product);
            const product = productDetails.deleted ? undefined : productDetails;
            return {
              id: item.id,
              quantity: item.quantity || 1,
              price: {
                id: price.id,
                amount: price.unit_amount || 0,
                currency: price.currency,
                interval: price.recurring?.interval || "month",
                intervalCount: price.recurring?.interval_count,
                trialPeriodDays:
                  price.recurring?.trial_period_days || undefined,
              },
              product: product
                ? {
                    id: product.id,
                    name: product.name || "",
                    description: product.description || "",
                    images: product.images || [],
                  }
                : undefined,
            } satisfies SubscriptionItemView;
          }),
        );

        const items = itemsResults.flatMap((result) => {
          if (result.status === "fulfilled") return [result.value];
          logger.error("Failed to fetch subscription item details", {
            subscriptionId: subscription.id,
            error: result.reason,
          });
          return [];
        });

        return {
          id: subscription.id,
          status: subscription.status,
          clientId: subscription.clientId,
          currentPeriodStart: new Date(
            (subscription.items.data[0]?.current_period_start ||
              subscription.start_date) * 1000,
          ),
          currentPeriodEnd: new Date(
            (subscription.items.data[0]?.current_period_end || 0) * 1000,
          ),
          cancelAt: subscription.cancel_at
            ? new Date(subscription.cancel_at * 1000)
            : undefined,
          canceledAt: subscription.canceled_at
            ? new Date(subscription.canceled_at * 1000)
            : undefined,
          cancelAtPeriodEnd: subscription.cancel_at_period_end,
          items,
          paymentMethod: await this.stripe.defaultCard(
            subscription.clientId,
            subscription,
          ),
        } satisfies SubscriptionView;
      }),
    );

    const subscriptions = subscriptionsResults.flatMap((result) => {
      if (result.status === "fulfilled") return [result.value];
      logger.error("Failed to fetch subscription details", {
        error: result.reason,
      });
      return [];
    });

    return { hasActiveSubscription, subscriptions };
  }

  public async createSubscriptionSession(
    identity: Identity,
    clientId: string,
    priceId: string,
  ): Promise<SubscriptionSessionResultView> {
    await this.authorize(
      identity,
      AUTHORIZATION_ACTIONS.USER_BILLING_CHECKOUT_CREATE,
    );
    const { userId } = identity;

    try {
      const clientConfig =
        SUBSCRIPTION_CONFIG[clientId as keyof typeof SUBSCRIPTION_CONFIG];
      if (!clientConfig) {
        return { success: false, message: `Invalid client ID: ${clientId}` };
      }
      if (!clientConfig.planIds.includes(priceId)) {
        return {
          success: false,
          message: `Invalid price ID for client ${clientId}: ${priceId}`,
        };
      }

      const planConfig = clientConfig.plans.find(
        (plan) => plan.priceId === priceId,
      );
      if (!planConfig) {
        return {
          success: false,
          message: `Plan configuration not found for price ID: ${priceId}`,
        };
      }

      const stripe = this.stripe.getStripeInstance(clientId);
      const existingCustomer =
        await this.models.paidCustomer.findByUserIdAndClientId(
          this.db,
          userId,
          clientId,
        );
      const sharedSession = {
        line_items: [{ price: priceId, quantity: 1 }],
        allow_promotion_codes: true,
        mode: planConfig.type,
        success_url: clientConfig.successUrl,
        cancel_url: clientConfig.cancelUrl,
        metadata: { userId, clientId },
        ...(planConfig.type === "subscription"
          ? { subscription_data: { metadata: { userId, clientId } } }
          : {}),
      };
      let session: Stripe.Checkout.Session;
      if (existingCustomer?.stripeCustomerId) {
        session = await stripe.checkout.sessions.create({
          ...sharedSession,
          customer: existingCustomer.stripeCustomerId,
        });
      } else {
        const user = await this.models.user.getById(this.db, userId);
        session = await stripe.checkout.sessions.create({
          ...sharedSession,
          customer_email: user?.email,
        });
      }

      return {
        success: true,
        sessionId: session.id,
        sessionUrl: session.url || undefined,
      };
    } catch (error) {
      logger.error("Error creating subscription session", {
        error: error instanceof Error ? error.message : String(error),
      });
      return {
        success: false,
        message: "An error occurred while creating the subscription session",
      };
    }
  }

  public async createStripePortalSession(
    identity: Identity,
    clientId: string,
  ): Promise<SubscriptionSessionResultView> {
    await this.authorize(
      identity,
      AUTHORIZATION_ACTIONS.USER_BILLING_PORTAL_CREATE,
    );
    return this.stripe.createCustomerPortalSession(identity.userId, clientId);
  }

  public async cancelSubscription(
    identity: Identity,
    subscriptionId: string,
    clientId: string,
  ): Promise<SubscriptionActionResultView> {
    await this.authorize(
      identity,
      AUTHORIZATION_ACTIONS.USER_BILLING_SUBSCRIPTION_CANCEL,
    );
    return this.stripe.cancelSubscription(
      subscriptionId,
      identity.userId,
      clientId,
    );
  }

  public async resumeSubscription(
    identity: Identity,
    subscriptionId: string,
    clientId: string,
  ): Promise<SubscriptionActionResultView> {
    await this.authorize(
      identity,
      AUTHORIZATION_ACTIONS.USER_BILLING_SUBSCRIPTION_RESUME,
    );
    return this.stripe.resumeSubscription(
      subscriptionId,
      identity.userId,
      clientId,
    );
  }

  public async upgradeSubscription(
    identity: Identity,
    clientId: string,
    priceId: string,
  ): Promise<UpgradeSubscriptionResultView> {
    await this.authorize(
      identity,
      AUTHORIZATION_ACTIONS.USER_BILLING_SUBSCRIPTION_UPGRADE,
    );
    return this.stripe.upgradeSubscription(identity.userId, clientId, priceId);
  }

  public async previewPlanChange(
    identity: Identity,
    clientId: string,
    priceId: string,
  ): Promise<PlanChangePreviewView> {
    await this.authorize(
      identity,
      AUTHORIZATION_ACTIONS.USER_BILLING_PLAN_CHANGE_PREVIEW,
    );
    return this.stripe.previewPlanChange(identity.userId, clientId, priceId);
  }
}
