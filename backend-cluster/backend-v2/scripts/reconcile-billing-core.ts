import { createHash } from "node:crypto";
import {
  BILLING_CLIENT_ID,
  SubscriptionTier,
} from "../src/features/stripe/service/stripe";
import {
  customerId,
  subscriptionPeriodEnd,
  holdsPaidTier,
  subscriptionTier,
  type ClientSubscription,
} from "../src/features/stripe/service/subscription-plan";

export interface BindingSnapshot {
  id: string;
  userId: string;
  clientId: string;
  stripeCustomerId: string;
  period: string | null;
  version: string;
}
export interface UserRepair {
  userId: string;
  classification:
    | "no-history"
    | "test-only"
    | "live-only"
    | "mixed"
    | "expired"
    | "unresolved";
  before: BindingSnapshot[];
  changes: { id: string; period: string | null }[];
  evidence: string;
}
export function fingerprint(value: unknown): string {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

/** The provider must return a complete, verified live customer's history or throw. */
export async function planUserRepair(
  userId: string,
  rows: BindingSnapshot[],
  load: (binding: BindingSnapshot) => Promise<ClientSubscription[]>,
): Promise<UserRepair> {
  const before = [...rows].sort((a, b) => a.id.localeCompare(b.id));
  const result: UserRepair = {
    userId,
    before,
    changes: [],
    classification: "no-history",
    evidence: "",
  };
  if (
    before.some(
      (row) =>
        row.userId !== userId ||
        ![BILLING_CLIENT_ID, "beancount-web-dev"].includes(row.clientId),
    )
  ) {
    return { ...result, classification: "unresolved" };
  }
  const live = before.filter((row) => row.clientId === BILLING_CLIENT_ID);
  const retired = before.filter((row) => row.clientId === "beancount-web-dev");
  if (live.length > 1 || retired.length > 1)
    return { ...result, classification: "unresolved" };
  const observations: unknown[] = [];
  let active = false;
  for (const row of live) {
    const subscriptions = await load(row); // Never convert an outage/missing customer into an empty history.
    if (
      subscriptions.some(
        (sub) =>
          !sub.livemode ||
          sub.clientId !== row.clientId ||
          customerId(sub.customer) !== row.stripeCustomerId ||
          (holdsPaidTier(sub) &&
            subscriptionTier(sub) === SubscriptionTier.FREE),
      )
    ) {
      return { ...result, classification: "unresolved" };
    }
    active = subscriptions.some(
      (sub) => subscriptionTier(sub) !== SubscriptionTier.FREE,
    );
    observations.push(
      subscriptions
        .map((sub) => ({
          id: sub.id,
          status: sub.status,
          items: sub.items.data.map((item) => ({
            price: item.price.id,
            end: item.current_period_end,
          })),
        }))
        .sort((a, b) => a.id.localeCompare(b.id)),
    );
    const period = subscriptionPeriodEnd(subscriptions)?.toISOString() ?? null;
    if (period !== row.period) result.changes.push({ id: row.id, period });
  }
  // Retain the historical binding for audit; only its obsolete access cache is retired.
  for (const row of retired)
    if (row.period !== null) result.changes.push({ id: row.id, period: null });
  result.classification = live.length
    ? retired.length
      ? "mixed"
      : active
        ? "live-only"
        : "expired"
    : retired.length
      ? "test-only"
      : "no-history";
  result.evidence = fingerprint(observations);
  return result;
}

export interface RepairStore {
  read(userId: string): Promise<BindingSnapshot[]>;
  // The implementation locks and compares ALL user bindings inside one transaction.
  compareAndSet(repair: UserRepair): Promise<BindingSnapshot[]>;
}
export async function applyUserRepair(
  reviewed: UserRepair,
  store: RepairStore,
  load: (binding: BindingSnapshot) => Promise<ClientSubscription[]>,
  recordRollback: (repair: UserRepair) => Promise<void>,
) {
  if (reviewed.classification === "unresolved")
    throw new Error("Unresolved billing ownership");
  const fresh = await planUserRepair(
    reviewed.userId,
    await store.read(reviewed.userId),
    load,
  );
  if (fingerprint(fresh) !== fingerprint(reviewed))
    throw new Error(
      "Billing state changed since preview; generate a new preview",
    );
  if (!fresh.changes.length) return fresh.before;
  await recordRollback(fresh); // Durable write before the database commit.
  return store.compareAndSet(fresh);
}

export function rollbackRepair(
  original: UserRepair,
  after: BindingSnapshot[],
): UserRepair {
  return {
    ...original,
    before: after,
    changes: original.changes.map((change) => ({
      id: change.id,
      period: original.before.find((row) => row.id === change.id)!.period,
    })),
  };
}
