/**
 * Event taxonomy — the single source of truth for product analytics events.
 *
 * Adding/changing an event means editing the `AnalyticsEvents` registry below.
 * Because `track()` is typed against this registry, event names and their
 * parameters are enforced at compile time, which prevents the taxonomy drift
 * that arises from calling the raw `trackEvent(name, params)` with free-form
 * strings.
 *
 * CURRENT FOCUS (v1): registration (`sign_up`), login (`login`), and page views.
 * route_view is NOT in this registry — it is a custom page-navigation event
 * owned by AnalyticsProvider (see analytics-provider.tsx + track.ts) that fires
 * alongside GA4's auto page_view with fully normalized, PII-free parameters.
 *
 * Conventions (see docs/event-taxonomy.md for the full spec):
 *  - snake_case, object_action, past tense for completed actions.
 *  - Reuse GA4 recommended names (sign_up, login, …) where they map cleanly so
 *    GA4's built-in reporting and predictive audiences light up.
 *  - Never send raw ledger/account names, per-user ids, or monetary amounts —
 *    prefer bucketed/derived attributes.
 */
import type { UserTier } from "@/common/hooks/use-user-limits";
import type { CancellationReason, PlanChangeKind } from "@/graphql/definitions";
import type {
  BillingCycle,
  SubscriptionTier,
} from "@/features/user-settings/pages/general/stripe-config";
import { trackEvent, setUserProperties as setRawUserProperties } from "./track";

/**
 * How a user authenticated. Only "password" is supported for now; add
 * other methods (e.g. "google", "github", "one_time_token") here when those
 * paths are instrumented.
 */
export type AuthMethod = "password";

/**
 * Kind of Beancount directive added through the "New directive" dialog.
 * Mirrors the four dialog tabs / the LedgerEntryType values the forms submit.
 */
export type DirectiveType = "transaction" | "balance" | "note" | "open";

/** Financial statement and browser output selected from a report page. */
export type ReportExportType =
  | "balance_sheet"
  | "profit_and_loss"
  | "cash_flow";
export type ReportExportFormat = "csv" | "markdown" | "print";
export type ReportExportFailure =
  | "csv_generation"
  | "markdown_generation"
  | "print_dialog";

/** Subscription tier. Mirrors UserTier so it stays in sync with billing. */
export type PlanTier = UserTier;

/** The in-product prompts that open Billing on a recommended plan. */
export const UPGRADE_SURFACES = [
  "ai_cfo_panel",
  "importer_paywall",
  "ledgers_limit",
  "collaborators_limit",
  "directive_usage",
] as const;
export type UpgradeSurface = (typeof UPGRADE_SURFACES)[number];

/**
 * Where a plan change started: a prompt's deep link, Billing's own plan rows
 * or yearly offer, or a deep link from elsewhere (the pricing page).
 */
export type BillingSurface =
  | UpgradeSurface
  | "settings_billing"
  | "pay_yearly_offer"
  | "cancel_sheet"
  | "deep_link";

/**
 * A plan as an analytics value: tier and cycle (`growth_yearly`), or the tier
 * alone when it has no billing cycle (`free`, `enterprise`, a paid tier held
 * without a Stripe subscription).
 */
export type PlanValue =
  | Lowercase<PlanTier>
  | `${SubscriptionTier}_${BillingCycle}`;

/** Why a subscriber cancels, as the cancel sheet offers it. */
export type CancelReason = Lowercase<`${CancellationReason}`>;

/** One plan change, as every plan-change event describes it. */
interface PlanChangeParams {
  kind: PlanChangeKind;
  from: PlanValue;
  to: PlanValue;
  surface: BillingSurface;
}

/**
 * Standard parameters that may accompany any event. Attach whatever is in
 * scope at the call site.
 *
 * NOTE: we deliberately do NOT carry a per-ledger id. A specific ledger's
 * identity is not a useful analytics dimension — it's high-cardinality, opaque,
 * and no growth/product decision turns on it. Cross-data analysis joins on
 * `user_id` (set via setUserId) in the warehouse, not on ledger_id. Prefer
 * bucketed/derived attributes (e.g. `source`, `visibility`) over ids.
 */
export interface StandardParams {
  /** Current subscription tier of the actor. */
  plan_tier?: PlanTier;
  /** Whether the actor owns the ledger or collaborates on it. */
  user_role?: "owner" | "collaborator";
  /** UI entry point that triggered the action, e.g. "sidebar", "welcome". */
  surface?: string;
}

/**
 * The canonical event registry.
 *
 * SCOPE (v1): intentionally limited to the two auth events we are focusing on
 * now. The broader activation / engagement / monetization events
 * (ledger_created, transaction_added, import_completed, bank_link_completed,
 * checkout_started, …) are documented as a roadmap in docs/event-taxonomy.md
 * and should be added here, one typed line each, as they are instrumented.
 */
export interface AnalyticsEvents {
  // --- Acquisition (GA4 recommended names) ---
  /**
   * Account created. Fired once registration actually completes — i.e. after
   * email OTP verification (use-otp-form.ts), NOT at form submit — so the metric
   * counts verified accounts and is not inflated by abandoned attempts.
   */
  sign_up: { method: AuthMethod };
  /**
   * Returning sign-in. Fired on password login and on one-time-token / OAuth
   * callback login. Powers DAU/WAU/MAU and retention.
   */
  login: { method: AuthMethod };
  /**
   * Coarse retirement signal for the old embedded-mobile token handoff. It is
   * emitted only when the WebView bridge exists and deliberately carries no
   * token, user, server, URL, or app-version value.
   */
  legacy_mobile_auth_completed: {
    flow: "password" | "otp" | "one_time_token";
  };

  // --- Activation / engagement ---
  /**
   * A directive was successfully added via the "New directive" dialog. Fired in
   * each form's mutation-success branch (transaction/balance/note/open-account),
   * so it counts only committed directives, not abandoned form opens. Slice by
   * `directive_type` to answer "did the user add a transaction?" specifically or
   * "any directive?" in aggregate. Raw ledger/account names are never sent.
   */
  directive_added: { directive_type: DirectiveType };
  /**
   * A raw ledger file edit was successfully saved in the file editor. Fired in
   * the save mutation's `onCompleted`, so it counts only genuine saves (the
   * editor guards against saving unchanged content). No file path is sent — it
   * can contain ledger/account structure (see docs/event-taxonomy.md §4).
   */
  file_edited: Record<string, never>;
  /**
   * A user sent a message to the AI agent on the /ledger/:owner/:name/agent
   * chat. Fired once per user-initiated send — both the chat-input submit and
   * the `?q=` deep-link auto-submit on load — but NOT on the SDK's automatic
   * post-approval continuation, which is not a user message. Powers agent
   * engagement frequency (messages per user / per session). `has_attachment`
   * distinguishes plain questions from file-processing requests; message text
   * and file contents are never sent (see docs/event-taxonomy.md §4).
   */
  ai_agent_message_sent: { has_attachment: boolean };
  /**
   * A user executed a BQL query. Fired once per real execution at the single
   * choke point (`bql/pages/index.tsx → executeQueryAndCache`), covering the
   * manual submit, history re-run, and `?query=` deep-link paths; success and
   * failure are counted alike. Engagement signal — frequency of BQL use per
   * user, measured by `event_name` alone. Intentionally parameter-less ("bare"):
   * the raw BQL text can embed account names (§4), and `success`/`duration_ms`
   * would each cost a GA4 custom-dimension slot (50-slot cap). `event_name` is a
   * free dimension, so this reports frequency with zero custom-dimension budget.
   */
  bql_query_executed: Record<string, never>;
  /** A user opened a release from the What's new block. No release identifiers. */
  changelog_release_opened: { surface: "dashboard" };
  /**
   * A user invoked a financial-statement export. These events intentionally
   * contain only bounded product dimensions: never ledger identifiers,
   * filenames, filter expressions, account names, or amounts.
   */
  report_export_started: {
    report_type: ReportExportType;
    format: ReportExportFormat;
  };
  report_export_completed: {
    report_type: ReportExportType;
    format: ReportExportFormat;
  };
  report_export_failed: {
    report_type: ReportExportType;
    format: ReportExportFormat;
    failure_category: ReportExportFailure;
  };

  // --- Monetization ---
  /**
   * A user clicked an "Upgrade" CTA that surfaces subscription intent at a
   * friction point and opens the billing page's change sheet on a recommended
   * plan (`/settings/billing?plan=…&from=<surface>`) rather than starting
   * checkout inline: the AI-CFO usage panel, the importer premium paywall, the
   * collaborators/ledger limit walls, and the sidebar directive-usage nudge.
   * Captures intent at the moment of interest — independent of whether a
   * checkout is ever started — so it measures the top of the monetization
   * funnel (which friction points drive upgrade interest). `target_tier` is the
   * recommended plan, omitted only when no tier is above the user's.
   */
  upgrade_prompt_clicked: { surface: UpgradeSurface; target_tier?: PlanTier };
  /**
   * A reader without a subscription confirmed a plan in Billing's change sheet
   * and is leaving for Stripe Checkout (`createSubscriptionSession`), the
   * single checkout entry point. `target_tier` is the plan being purchased and
   * `surface` is where the change started. It is the funnel stage below
   * `upgrade_prompt_clicked`: intent → checkout_started → `purchase` (sent
   * from the browser once the payment is confirmed). An existing subscriber's in-place
   * change (`changePlan`) is not a checkout; it is `plan_change_confirmed`.
   * `target_tier` is distinct from the standard `plan_tier`, which is the
   * actor's *current* tier.
   */
  checkout_started: { target_tier: PlanTier; surface: BillingSurface };
  /**
   * GA4's recommended purchase: an invoice the customer paid us for a plan,
   * from Checkout's confirmation or an immediate upgrade in the change sheet.
   * The one event that carries money (what the customer paid us, never a
   * ledger amount). Sent once per invoice from this browser; a $0 invoice is
   * not a purchase.
   */
  purchase: {
    /** The Stripe invoice id; GA4 deduplicates purchases on it. */
    transaction_id: string;
    /** Major units, discounts applied. */
    value: number;
    /** ISO 4217, upper case. */
    currency: string;
    items: PurchaseItem[];
  };
  /**
   * The monthly/yearly switch above Billing's plan rows changed. Yearly is the
   * default, so this counts the readers who look at monthly first (PRFAQ005
   * question 19).
   */
  billing_toggle_changed: { to: BillingCycle; surface: "settings_billing" };
  /**
   * The change sheet received the server's preview of a change it can
   * describe (a `kind`); a refused preview is not counted. Fired once per
   * preview response, so a retry after an error counts again.
   */
  plan_change_previewed: PlanChangeParams;
  /**
   * The reader confirmed a previewed change: the sheet's pay-and-switch
   * button, its schedule button for a change at the period end, or its
   * checkout button for a `NEW` subscription (which then also sends
   * `checkout_started`). Paired with `plan_change_previewed` it gives the
   * preview → confirm rate per kind.
   */
  plan_change_confirmed: PlanChangeParams;
  /**
   * The bank must approve the change's payment. The sheet asks for it with
   * Stripe.js, or links to Stripe's page when Stripe.js cannot run.
   */
  payment_action_required: PlanChangeParams;
  /** The bank approved the payment in the sheet, so the change landed. */
  payment_action_completed: PlanChangeParams;
  /** The change's payment was declined, at once or by the bank; nothing changed. */
  payment_action_failed: PlanChangeParams;
  /** A change that waits for the end of the paid period was scheduled. */
  plan_change_scheduled: PlanChangeParams;
  /** The reader kept their plan, undoing a scheduled change to `to`. */
  plan_change_reverted: { from: PlanValue; to: PlanValue };
  /** The cancel sheet opened. */
  cancel_started: { from: PlanValue };
  /**
   * The subscription was set to end at the period's end, with the reader's
   * optional reason. Recorded on the server's success.
   */
  cancel_confirmed: { from: PlanValue; reason?: CancelReason };
  /** A pending cancellation was withdrawn with Resume. */
  subscription_resumed: { from: PlanValue };
}

/** The plan line of a `purchase`, in GA4's item shape. */
export interface PurchaseItem {
  /** The Stripe price id. */
  item_id: string;
  /** The plan, e.g. "premium". */
  item_name: string;
  /** The billing cycle; omitted for a price this app does not know. */
  item_variant?: "month" | "year";
  price: number;
  quantity: 1;
}

export type AnalyticsEventName = keyof AnalyticsEvents;

/**
 * Type-safe event tracker. The event name and its parameters are checked at
 * compile time against `AnalyticsEvents`. Prefer this over raw `trackEvent`
 * for every product event.
 *
 * @example
 * track("sign_up", { method: "password" });
 */
export function track<E extends AnalyticsEventName>(
  name: E,
  params: AnalyticsEvents[E] & StandardParams,
): void {
  trackEvent(name, params as unknown as Record<string, unknown>);
}

/**
 * User properties are set once on the GA4 user (not per event) and enable
 * cohort comparisons (e.g. retention by plan tier) without warehouse work.
 */
export interface AnalyticsUserProperties {
  plan_tier?: PlanTier;
  /** ISO date string, e.g. "2026-06-29". */
  signup_date?: string;
  ledger_count?: number;
  has_linked_bank?: boolean;
  /** i18n language code, e.g. "en", "zh". */
  preferred_language?: string;
}

/** Set typed GA4 user properties for cohorting. */
export function setUserProperties(props: AnalyticsUserProperties): void {
  setRawUserProperties(props as Record<string, unknown>);
}
