import {
  Arg,
  Ctx,
  Field,
  ID,
  Info,
  Int,
  Mutation,
  ObjectType,
  Query,
  Resolver,
  registerEnumType,
} from "type-graphql";
import { type GraphQLResolveInfo, Kind } from "graphql";
import type { ISubscriptionService } from "@/features/stripe/service/subscription-service";
import type {
  PlanChangeEffect,
  PlanChangeKind,
  PlanChangeRefusal,
} from "@/features/stripe/service/plan-change";
import type { PlanChangeStatus } from "@/features/stripe/operations/plan-change-apply";
import type { IContext } from "@/server/graphql/context";
import { AllowAnonymous, Authenticated } from "@/server/graphql/authenticated";

@ObjectType("SubscriptionPrice")
class SubscriptionPrice {
  @Field(() => ID)
  id!: string;

  @Field()
  amount!: number;

  @Field()
  currency!: string;

  @Field()
  interval!: string;

  @Field({ nullable: true })
  intervalCount?: number;

  @Field({ nullable: true })
  trialPeriodDays?: number;
}

@ObjectType("SubscriptionProduct")
class SubscriptionProduct {
  @Field(() => ID)
  id!: string;

  @Field()
  name!: string;

  @Field({ nullable: true })
  description?: string;

  @Field(() => [String], { nullable: true })
  images?: string[];
}

@ObjectType("SubscriptionItem")
class SubscriptionItem {
  @Field(() => ID)
  id!: string;

  @Field(() => SubscriptionPrice)
  price!: SubscriptionPrice;

  @Field(() => SubscriptionProduct, { nullable: true })
  product?: SubscriptionProduct;

  @Field()
  quantity!: number;
}

@ObjectType("PaymentMethodSummary")
class PaymentMethodSummary {
  @Field()
  brand!: string;

  @Field()
  last4!: string;
}

@ObjectType("ScheduledPlanChange", {
  description:
    "A plan change that takes effect at the end of the paid period. Nothing is charged until then.",
})
class ScheduledPlanChange {
  @Field()
  priceId!: string;

  @Field()
  effectiveAt!: Date;
}

@ObjectType("Subscription")
class Subscription {
  @Field(() => ID)
  id!: string;

  @Field()
  status!: string;

  @Field()
  currentPeriodStart!: Date;

  @Field()
  currentPeriodEnd!: Date;

  @Field({ nullable: false })
  clientId!: string;

  @Field({ nullable: true })
  cancelAt?: Date;

  @Field({ nullable: true })
  canceledAt?: Date;

  @Field()
  cancelAtPeriodEnd!: boolean;

  @Field(() => [SubscriptionItem])
  items!: SubscriptionItem[];

  @Field(() => PaymentMethodSummary, {
    nullable: true,
    description: "The card renewals and plan changes charge, when known.",
  })
  paymentMethod?: PaymentMethodSummary | null;

  @Field(() => ScheduledPlanChange, {
    nullable: true,
    description:
      "The change scheduled for the end of the paid period; cancelScheduledPlanChange undoes it.",
  })
  scheduledChange?: ScheduledPlanChange | null;
}

@ObjectType("CustomerSubscriptionStatus")
class CustomerSubscriptionStatus {
  @Field()
  hasActiveSubscription!: boolean;

  @Field(() => [Subscription])
  subscriptions!: Subscription[];
}

@ObjectType("SubscriptionActionResult")
class SubscriptionActionResult {
  @Field()
  success!: boolean;

  @Field({ nullable: true })
  message?: string;
}

@ObjectType("UpgradeSubscriptionResult")
class UpgradeSubscriptionResult {
  @Field()
  success!: boolean;

  @Field({ nullable: true })
  message?: string;

  @Field({ nullable: true })
  clientSecret?: string;

  @Field({ nullable: true })
  subscriptionId?: string;

  @Field({ nullable: true })
  newTier?: string;
}

@ObjectType("SubscriptionSessionResult")
class SubscriptionSessionResult {
  @Field()
  success!: boolean;

  @Field({ nullable: true })
  message?: string;

  @Field({ nullable: true })
  sessionId?: string;

  @Field({ nullable: true })
  sessionUrl?: string;
}

const PlanChangeKindValues: { [K in PlanChangeKind]: K } = {
  NEW: "NEW",
  UPGRADE: "UPGRADE",
  TO_YEARLY: "TO_YEARLY",
  DOWNGRADE: "DOWNGRADE",
  TO_MONTHLY: "TO_MONTHLY",
  SPLIT: "SPLIT",
};
registerEnumType(PlanChangeKindValues, { name: "PlanChangeKind" });

const PlanChangeRefusalValues: { [K in PlanChangeRefusal]: K } = {
  CURRENT_PLAN: "CURRENT_PLAN",
  SAME_TIER_AND_CYCLE: "SAME_TIER_AND_CYCLE",
  MULTIPLE_SUBSCRIPTIONS: "MULTIPLE_SUBSCRIPTIONS",
  NO_SUBSCRIPTION: "NO_SUBSCRIPTION",
  SCHEDULED_CHANGE: "SCHEDULED_CHANGE",
};
registerEnumType(PlanChangeRefusalValues, { name: "PlanChangeRefusal" });

const PlanChangeEffectValues: { [K in PlanChangeEffect]: K } = {
  CHECKOUT: "CHECKOUT",
  IMMEDIATE: "IMMEDIATE",
  SCHEDULED: "SCHEDULED",
};
registerEnumType(PlanChangeEffectValues, { name: "PlanChangeEffect" });

@ObjectType("PlanLimitChange")
class PlanLimitChange {
  @Field()
  limit!: string;

  @Field(() => Int, { description: "-1 means unlimited." })
  from!: number;

  @Field(() => Int, { description: "-1 means unlimited." })
  to!: number;
}

@ObjectType("PlanChangePreview", {
  description:
    "What choosing a price would do, before anything changes. Amounts are in the currency's minor unit (cents).",
})
class PlanChangePreview {
  @Field(() => PlanChangeKindValues, { nullable: true })
  kind!: PlanChangeKind | null;

  @Field(() => PlanChangeRefusalValues, { nullable: true })
  refusal!: PlanChangeRefusal | null;

  @Field(() => PlanChangeEffectValues, { nullable: true })
  effect!: PlanChangeEffect | null;

  @Field(() => String, { nullable: true })
  currentPriceId!: string | null;

  @Field()
  targetPriceId!: string;

  @Field()
  currency!: string;

  @Field(() => Int)
  amountDueToday!: number;

  @Field(() => Int)
  creditApplied!: number;

  @Field(() => Int)
  nextAmount!: number;

  @Field(() => Date, { nullable: true })
  nextChargeAt!: Date | null;

  @Field(() => Date, { nullable: true })
  effectiveAt!: Date | null;

  @Field(() => Int, {
    nullable: true,
    description:
      "Unix seconds. Pass it to changePlan so the charge matches this preview.",
  })
  prorationDate!: number | null;

  @Field(() => String, {
    nullable: true,
    description:
      "For SPLIT: the higher tier on the current billing cycle, applied now.",
  })
  alternativePriceId!: string | null;

  @Field(() => [PlanLimitChange])
  limitChanges!: PlanLimitChange[];

  @Field(() => PaymentMethodSummary, { nullable: true })
  paymentMethod!: PaymentMethodSummary | null;

  @Field(() => ScheduledPlanChange, {
    nullable: true,
    description: "The scheduled change this choice would replace.",
  })
  replacesScheduledChange!: ScheduledPlanChange | null;

  @Field({ description: "Whether this choice withdraws a pending cancellation." })
  withdrawsCancellation!: boolean;
}

const PlanChangeStatusValues: { [K in PlanChangeStatus]: K } = {
  ACTIVE: "ACTIVE",
  SCHEDULED: "SCHEDULED",
  REQUIRES_ACTION: "REQUIRES_ACTION",
  FAILED: "FAILED",
  REFUSED: "REFUSED",
};
registerEnumType(PlanChangeStatusValues, { name: "PlanChangeStatus" });

@ObjectType("PlanChangeResult")
class PlanChangeResult {
  @Field(() => PlanChangeStatusValues)
  status!: PlanChangeStatus;

  @Field(() => PlanChangeKindValues, { nullable: true })
  kind!: PlanChangeKind | null;

  @Field(() => PlanChangeRefusalValues, { nullable: true })
  refusal!: PlanChangeRefusal | null;

  @Field(() => String, { nullable: true })
  message!: string | null;

  @Field(() => String, {
    nullable: true,
    description: "With REQUIRES_ACTION: confirm the payment with Stripe.js.",
  })
  clientSecret!: string | null;

  @Field(() => String, {
    nullable: true,
    description:
      "Stripe's hosted page to pay or authenticate this change's invoice.",
  })
  hostedInvoiceUrl!: string | null;

  @Field(() => String, { nullable: true })
  subscriptionId!: string | null;

  @Field(() => String, { nullable: true })
  newTier!: string | null;

  @Field(() => Date, { nullable: true })
  currentPeriodEnd!: Date | null;

  @Field(() => Date, {
    nullable: true,
    description:
      "With SCHEDULED: when the new price takes over. Nothing is charged until then.",
  })
  effectiveAt!: Date | null;
}

@ObjectType("TierQuotaItem")
class TierQuotaItem {
  @Field(() => String)
  tier!: string;

  @Field(() => Number)
  aiCfoTokensMax!: number;

  @Field(() => Number)
  maxLedgers!: number;

  @Field(() => Number)
  maxCollaboratorsPerLedger!: number;

  @Field(() => Number)
  maxDirectives!: number;
}

function isOnlyHasActiveSubscriptionRequested(
  info: GraphQLResolveInfo,
): boolean {
  const selections = info.fieldNodes[0]?.selectionSet?.selections ?? [];
  if (selections.length !== 1) return false;
  const selection = selections[0];
  return (
    selection.kind === Kind.FIELD &&
    selection.name.value === "hasActiveSubscription"
  );
}

/** GraphQL is an adapter; all billing policy and work live in the service. */
@Resolver()
export class SubscriptionResolver {
  constructor(private readonly subscriptions: ISubscriptionService) {}

  @AllowAnonymous()
  @Query(() => [TierQuotaItem], {
    description: "Returns the public quota limits for all subscription tiers.",
  })
  async allTierQuotas(): Promise<TierQuotaItem[]> {
    return this.subscriptions.allTierQuotas();
  }

  @Authenticated()
  @Query(() => CustomerSubscriptionStatus, {
    description:
      "Returns your subscription status. Requires a full signed-in session.",
  })
  async subscriptionStatus(
    @Ctx() context: IContext,
    @Info() info: GraphQLResolveInfo,
  ): Promise<CustomerSubscriptionStatus> {
    return this.subscriptions.subscriptionStatus(
      context.getCurrentIdentity(),
      isOnlyHasActiveSubscriptionRequested(info),
    );
  }

  @Authenticated()
  @Query(() => PlanChangePreview, {
    description:
      "Previews switching your plan to a price: the kind of change, when it takes effect, and what is charged today. Requires a full signed-in session.",
  })
  async previewPlanChange(
    @Arg("clientId") clientId: string,
    @Arg("priceId") priceId: string,
    @Ctx() context: IContext,
  ): Promise<PlanChangePreview> {
    return this.subscriptions.previewPlanChange(
      context.getCurrentIdentity(),
      clientId,
      priceId,
    );
  }

  @Authenticated()
  @Mutation(() => PlanChangeResult, {
    description:
      "Applies an upgrade or a switch to yearly at the previewed proration time, and schedules a downgrade or a switch to monthly for the end of the paid period. Requires a full signed-in session.",
  })
  async changePlan(
    @Arg("clientId") clientId: string,
    @Arg("priceId") priceId: string,
    @Arg("prorationDate", () => Int, {
      nullable: true,
      description: "The prorationDate from previewPlanChange.",
    })
    prorationDate: number | null | undefined,
    @Ctx() context: IContext,
  ): Promise<PlanChangeResult> {
    return this.subscriptions.changePlan(
      context.getCurrentIdentity(),
      clientId,
      priceId,
      prorationDate,
    );
  }

  @Authenticated()
  @Mutation(() => SubscriptionActionResult, {
    description:
      "Cancels the plan change scheduled for the end of the paid period; the current plan continues unchanged. Requires a full signed-in session.",
  })
  async cancelScheduledPlanChange(
    @Arg("clientId") clientId: string,
    @Ctx() context: IContext,
  ): Promise<SubscriptionActionResult> {
    return this.subscriptions.cancelScheduledPlanChange(
      context.getCurrentIdentity(),
      clientId,
    );
  }

  @Authenticated()
  @Mutation(() => SubscriptionSessionResult, {
    description:
      "Creates a Stripe-hosted checkout session. Requires a full signed-in session.",
  })
  async createSubscriptionSession(
    @Arg("clientId") clientId: string,
    @Arg("priceId") priceId: string,
    @Ctx() context: IContext,
  ): Promise<SubscriptionSessionResult> {
    return this.subscriptions.createSubscriptionSession(
      context.getCurrentIdentity(),
      clientId,
      priceId,
    );
  }

  @Authenticated()
  @Mutation(() => SubscriptionSessionResult, {
    description:
      "Creates a Stripe-hosted customer portal session. Requires a full signed-in session.",
  })
  async createStripePortalSession(
    @Arg("clientId") clientId: string,
    @Ctx() context: IContext,
  ): Promise<SubscriptionSessionResult> {
    return this.subscriptions.createStripePortalSession(
      context.getCurrentIdentity(),
      clientId,
    );
  }

  @Authenticated()
  @Mutation(() => SubscriptionActionResult, {
    description:
      "Schedules your subscription to cancel. Requires a full signed-in session.",
  })
  async cancelSubscription(
    @Arg("subscriptionId") subscriptionId: string,
    @Arg("clientId") clientId: string,
    @Ctx() context: IContext,
  ): Promise<SubscriptionActionResult> {
    return this.subscriptions.cancelSubscription(
      context.getCurrentIdentity(),
      subscriptionId,
      clientId,
    );
  }

  @Authenticated()
  @Mutation(() => SubscriptionActionResult, {
    description:
      "Resumes your subscription. Requires a full signed-in session.",
  })
  async resumeSubscription(
    @Arg("subscriptionId") subscriptionId: string,
    @Arg("clientId") clientId: string,
    @Ctx() context: IContext,
  ): Promise<SubscriptionActionResult> {
    return this.subscriptions.resumeSubscription(
      context.getCurrentIdentity(),
      subscriptionId,
      clientId,
    );
  }

  @Authenticated()
  @Mutation(() => UpgradeSubscriptionResult, {
    description:
      "Upgrades your subscription. Requires a full signed-in session.",
  })
  async upgradeSubscription(
    @Arg("clientId") clientId: string,
    @Arg("priceId") priceId: string,
    @Ctx() context: IContext,
  ): Promise<UpgradeSubscriptionResult> {
    return this.subscriptions.upgradeSubscription(
      context.getCurrentIdentity(),
      clientId,
      priceId,
    );
  }
}
