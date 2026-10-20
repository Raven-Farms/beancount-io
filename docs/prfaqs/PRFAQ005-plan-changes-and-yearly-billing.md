# PRFAQ005 — Change plans and pay yearly from inside the product

Status: Stage 1 shipped and deployed on 2026-10-18 (w1/m39, through `bcb5462c7`). It covers server-side previews, immediate changes, the Billing tab, the Checkout confirmation and the $143.88 Premium yearly price, which the marketing pricing page sells too. Stage 2's code is on `main` (w1/m40, through `87eac2708`). It covers scheduled downgrades and switches to monthly with undo, the cancel sheet, paid limits while past due with the failed-renewal banner, the ledger-count and collaborator-limit fixes, and the scheduled-change emails. Its deploy, two Stripe Dashboard settings and the production payment test are pending. All pricing and policy decisions were recorded on 2026-10-17 ([question 21](#21-what-has-been-decided)). On 2026-10-20 (w2/m54) Checkout started returning to the dashboard confirmation, `purchase` moved to the browser, and a paid transaction gets a one-time confetti celebration.

Date: 2026-10-17

Scope: The whole web subscription experience: the marketing pricing page (`beancount.io/pricing`), Stripe Checkout, the dashboard's billing settings, the Stripe customer portal and billing email. It covers every change a subscriber can make: subscribe, upgrade, switch from monthly to yearly, downgrade, switch from yearly to monthly, cancel, resume and recover from a failed payment. Mobile billing ([ADR001](../adrs/ADR001-mobile-billing.md)) is out of scope.

Evidence baseline: `beancount-io` commit `c6cb903d3` and the live pricing page at `beancount.io/pricing`, both read-only, on 2026-10-17. Stripe account settings were not inspected. That includes the default customer-portal configuration, whether each configured price is still active, and which customer emails are enabled. No customer interviews have been run, and no conversion or revenue effect is measured or implied.

**Recommendation:** Make every plan change the same flow. A plan is a tier plus a billing cycle. The customer picks one, sees a preview computed by the server that shows what changes and what is charged, and confirms. Gains apply immediately; losses apply at the end of the period already paid for. Ship it in three stages. The first stage fixes the defects that make today's yearly option a dead end for existing subscribers, and moves Premium's yearly price to the same 20% saving as the other tiers.

This proposal adds no tier. It changes one price: a new Premium yearly subscription costs $143.88 a year ($11.99 a month), while subscribers already on the $99.99 yearly price keep it. It supersedes the yearly-billing analysis in the withdrawn Business-tier proposal (removed in `adb8ce0b8`); nothing that proposal described was implemented.

## Press release

*Proposed launch copy, written as if released. Capabilities and wording remain proposals; this is not a current product announcement.*

**Beancount.io subscribers can now switch to yearly billing, upgrade or downgrade in one step, and see the exact charge before they confirm**

*Pick a plan and a billing cycle, see what changes and what you pay today, and confirm. Nothing about your books changes unless you choose it.*

Beancount.io today made every plan change self-service. From Billing settings, a subscriber chooses any plan on monthly or yearly billing and sees three things before confirming: what the plan adds or removes, what is charged today, and when the next charge falls. The amount on the confirm button is the amount charged.

Monthly subscribers can move to yearly billing in one click, and the unused part of the current month is credited against the first yearly charge. Every paid plan costs twenty percent less on yearly billing: Premium is $143.88 a year instead of $179.88 for twelve monthly payments.

Upgrades take effect immediately. Downgrades and switches from yearly to monthly take effect when the period already paid for ends, so nobody loses time they have paid for, and the change can be undone until then. Downgrading never deletes anything. If you have more ledgers or collaborators than the new plan includes, they all keep working; you just can't add more until you are back under the limit.

The plan someone chooses on the pricing page now survives sign-up, and after payment Beancount.io confirms the plan, the renewal date and what was unlocked. It then takes the customer back to where they were working. If a bank asks the customer to approve a payment, the approval happens on the same page. If a renewal payment fails, the subscriber keeps their plan while the card is retried and sees exactly what to fix and by when.

## Customer FAQ

### 1. How do I switch from monthly to yearly?

Open **Settings → Billing**. A monthly plan shows a "Pay yearly" line with the yearly saving and a **Switch to yearly** button. Alternatively, choose **Change plan** and select **Yearly**. The switch takes effect immediately, and your renewal date becomes one year from today.

### 2. What will I be charged when I switch?

You are charged the yearly price, minus a credit for the unused part of your current month. For example, 10 days into a 30-day Premium month: $143.88 − $9.99 credit = **$133.89 today**, then $143.88 a year. Stripe prorates to the second, so the confirmation shows the exact figure, and the confirmed figure is what is charged.

| Plan | Monthly | Yearly | Per month on yearly | Yearly saving |
| --- | --- | --- | --- | --- |
| Premium | $14.99 | $143.88 | $11.99 | $36.00 (20%) |
| Growth | $99.99 | $959.88 | $79.99 | $240.00 (20%) |
| Organization | $499.99 | $4,799.88 | $399.99 | $1,200.00 (20%) |

Subscribers already on the $99.99 yearly Premium price keep it at renewal; see question 11.

### 3. What happens when I upgrade?

The new plan applies immediately. You pay the difference for the rest of the current period: for example, Premium to Growth halfway through a month is about $42.50 today. Your renewal date stays the same. If you upgrade and move from monthly to yearly at the same time, the renewal date becomes one year from today, as in question 2.

### 4. Can I downgrade? When does it take effect?

Yes, from Billing settings. A downgrade takes effect at the end of the period you have already paid for, and you keep your current plan until then. Nothing is charged today. Billing settings shows the scheduled change with a **Keep current plan** button that undoes it at any time before that date.

### 5. What happens if I'm over the new plan's limits?

Nothing is deleted. Usage limits only stop you adding more, and plan features follow the pricing table:

- **Ledgers:** every ledger keeps working. You can't create another until you have fewer than the new plan allows.
- **Collaborators:** everyone keeps their access and permissions. You can't add someone to a ledger that is at or over the new limit.
- **AI Assistant:** the allowance is counted per calendar month, so what you used earlier in the month counts against the new allowance. If you are already past it, the Assistant pauses until the first of the next month.
- **Entries on Free:** a ledger over 1,000 entries stays readable, and you can still edit and delete entries on Beancount.io. Adding entries, and `git push` to that ledger, are refused until you delete enough entries to be under 1,000.
- **API keys:** the keys you already have keep working. Creating a new one needs a paid plan.
- **Plan features** such as advanced automation & integrations or OIDC SSO: these come with the plans the pricing table lists them under, so they end with the higher plan. Your books are unaffected.

Before you confirm, the downgrade screen lists every limit that goes down next to your current usage, so there are no surprises on the effective date.

### 6. Can I switch from yearly back to monthly?

Yes. The switch happens at your renewal date. If it happened immediately, the unused months of your year would turn into an account credit rather than a refund, so waiting for the renewal date keeps the money you paid in the plan you paid for.

If you also want a higher plan right away, you are offered both options:

- the higher plan on yearly billing today, or
- the higher plan on monthly billing from your renewal date.

### 7. I chose a plan on the pricing page before I had an account. Do I have to choose again?

No. The plan and billing cycle you picked carry through sign-up and sign-in. When you come back to the pricing page, a **Continue to checkout** bar for that plan takes you to payment in one click.

### 8. My bank asked me to approve the payment. What happens?

Your bank's approval window opens on the same page. If you approve, the change applies immediately. If you don't, nothing changes, and you can try again or pay with another card.

### 9. What happens if a renewal payment fails?

A banner across the app tells you which card failed and the date by which to update it. You keep your plan while Stripe retries the card on its usual schedule, and **Update payment method** in the banner fixes it.

### 10. How do I cancel, and what do I keep?

Choose **Cancel subscription** at the bottom of Billing settings. You keep your plan until the end of the period you have paid for, then move to Free. Your books are plain text, and you can export them at any time. Until the end date, **Resume** undoes the cancellation.

The cancel screen offers one cheaper alternative, either yearly billing or a lower plan, and asks an optional reason. The cancel button is as prominent as the button to keep your plan.

### 11. I'm on an older price. Will changing my plan affect it?

Only if you change plan. Older prices include Premium at $9.99 a month and Premium at $99.99 a year. The confirmation tells you that the older price ends with the change and can't be chosen again. If you don't change plan, you keep it.

### 12. Do you refund unused time?

No. Beancount.io doesn't refund payments. When you change plan, unused time is credited against the new charge. When you cancel, you keep your plan until the end of the period you have paid for.

## Internal FAQ

### 13. Why is today's yearly option a dead end?

Yearly price IDs exist for every paid tier in the pricing page's checkout, the backend `SUBSCRIPTION_CONFIG` and the dashboard `stripe-config.ts`. The backend accepts every configured price in both `createSubscriptionSession` and `upgradeSubscription`.

The pricing page has a monthly/yearly toggle, and starts a yearly checkout for a signed-in visitor without a subscription. The pricing page's `next` destination survives sign-up and the sign-up/sign-in hop:

- `dashboard/src/features/auth/pages/register/loader.ts`
- `register-otp.tsx`
- `dashboard/src/features/auth/components/register-form/index.tsx`

Everything after that point is broken or missing:

| # | Defect | Evidence |
| --- | --- | --- |
| 1 | The dashboard starts every new subscription and every upgrade on the monthly price. | `dashboard/src/features/user-settings/pages/general/subscription-section.tsx:137` and `:158` pass `stripeConfig[tierKey].monthly` |
| 2 | The dashboard lists only higher tiers, so neither a same-tier switch to yearly nor any downgrade has a control. | `dashboard/src/common/lib/subscription/tier-config.ts:50` (`getUpgradeTiers`) |
| 3 | Every subscriber, and every in-product upgrade prompt, is sent to those settings. | The pricing page's "Manage subscription" link for an existing subscriber goes to `/settings/general`; `dashboard/docs/event-taxonomy.md` records that every other upgrade prompt navigates there too |
| 4 | After payment, Checkout returns the customer to the marketing page, which shows no confirmation. | `successUrl: "https://beancount.io/pricing/?success=true"` in `backend-cluster/backend-v2/src/features/stripe/service/stripe.ts:201`; the pricing page does not read `success` |
| 5 | A failed checkout on the pricing page does nothing visible. | The pricing page redirects only when `createSubscriptionSession` returns a `sessionUrl`; a `success: false` result or a rejected request leaves the button with no message |
| 6 | A change that needs bank authentication is reported as a failure. | See below |
| 7 | A failed renewal drops the subscriber to Free at once. | `subscriptionTier` returns `FREE` for any status other than `active` (`backend-cluster/backend-v2/src/features/stripe/service/subscription-plan.ts:14`), so `past_due` loses paid limits before Stripe's first retry |
| 8 | The customer portal's plan switching is uncontrolled. | `billingPortal.sessions.create` passes no `configuration` (`stripe-service.ts:714`), so switching follows the account's default portal settings, which were not inspected. A switch to a price outside `SUBSCRIPTION_CONFIG` would resolve to `FREE` |
| 9 | The two surfaces disagree on which plan is most popular. | The pricing page marks Premium; the dashboard marks Growth (`tier-config.ts:35`) |

On defect 6: `upgradeSubscription` looks for `latest_invoice.payment_intent` (`stripe-service.ts:346–363`) in two cases that can't co-occur:

- The update at `:300` does not expand `latest_invoice`, so it arrives as an ID string.
- Under API version `2025-12-15.clover`, an Invoice no longer carries `payment_intent`; the stripe-node 20.2.0 types expose `payments` instead.

So a change that requires authentication returns "Payment failed. Your subscription was not changed.", while Stripe holds the change as a pending update (`payment_behavior: "pending_if_incomplete"`). The dashboard's `clientSecret` branch (`subscription-section.tsx:165–166`) would only show a toast even if it were reached.

Both repository configurations, and the pricing page's checkout, label the Premium yearly price (`price_1L9ccEEqsEqs2tLVbeBgHm9p`, $99.99) "Legacy", and whether it is still active in live mode was not checked. If it has been archived, the one yearly path that works today fails as well, reported only by the generic error in defect 5. Stage 1 replaces it for new subscriptions with the $143.88 price decided in question 21, and keeps it recognized so existing yearly subscribers still resolve to Premium.

### 14. What are the plan-change rules?

A plan is (tier, cycle), with tiers ordered Free < Premium < Growth < Organization (the backend's `SubscriptionTier` order). The backend classifies a change from that order and the two prices' intervals. It is the only place that classification is computed: the pricing page and the dashboard render the classification and preview the backend returns; they never recompute them.

| Change | Takes effect | Charged today | Renewal date |
| --- | --- | --- | --- |
| Free → paid, either cycle | Immediately, through Checkout | Full price | From today |
| Higher tier, same cycle | Immediately | Prorated difference | Unchanged |
| Monthly → yearly, same or higher tier | Immediately | Yearly price minus credit for unused time | One year from today |
| Lower tier, either cycle | End of the paid period | Nothing | Unchanged |
| Yearly → monthly, same tier | End of the paid period | Nothing | Unchanged |
| Higher tier and yearly → monthly | Customer chooses: higher tier yearly now, or higher tier monthly at renewal | Depends on choice | Depends on choice |
| Cancel | End of the paid period; resumable until then | Nothing | — |
| Any change while another is scheduled | The new change replaces the scheduled one, and the preview says so | Per the new change | Per the new change |
| Any change while cancellation is pending | Cancellation is withdrawn, and the preview says so | Per the change | Per the change |

The rule underneath is: gains now, losses at period end. A yearly-to-monthly switch counts as a loss. Applied immediately, it turns months already paid for into a customer balance instead of keeping them in the plan the customer bought. Nothing is refunded in any case (question 21).

Enterprise remains "Contact us". Promotion codes remain a Checkout-only feature.

### 15. What does each surface look like?

Every string below ships in every locale each surface supports, with dates and amounts formatted for the reader's locale; prices stay in USD. Wireframes show layout and English copy; the examples use 2026-10-17 as today.

**Pricing page.** Yearly is selected by default. The cycle toggle is reflected in the URL (`?billing=yearly|monthly`) so it survives sharing and sign-up. Each card states its saving, computed from its prices. Growth carries the "Most popular" badge on both the pricing page and the dashboard.

```text
            ┌────────────┬────────────────────────────────┐
            │  Monthly   │ ● Yearly  · save 20%           │
            └────────────┴────────────────────────────────┘
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│ Premium             │ │ Growth  MOST POPULAR│ │ Organization        │
│ Individuals & Solo  │ │ Small Business      │ │ Multi-Entity        │
│ $11.99 /mo          │ │ $79.99 /mo          │ │ $399.99 /mo         │
│ $143.88 billed yrly │ │ $959.88 billed yrly │ │ $4,799.88 billed yr │
│ [ Save 20% ]        │ │ [ Save 20% ]        │ │ [ Save 20% ]        │
│ [  Get Premium   ]  │ │ [  Get Growth    ]  │ │ [ Get Organization ]│
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

The call to action depends on who is looking:

| Visitor | Button | Result |
| --- | --- | --- |
| Signed out | **Get Premium**, with "You'll create a free account first" beneath | Sign-up with `next=/pricing?plan=premium&billing=yearly&resume=checkout` |
| Returning from sign-up | A bar: "Continue to checkout — Premium · Yearly · $143.88 [Continue]" | One click to Checkout. No automatic redirect: a page that leaves on its own reads as hijacked |
| Signed in, no subscription | **Get Premium** | Checkout directly. A failure shows an inline error with **Try again** on the card |
| Subscriber, current plan | **● Current plan**, or **Switch to yearly** when on monthly | Dashboard change sheet, prefilled |
| Subscriber, other tier | **Upgrade** or **Downgrade** | Dashboard change sheet, prefilled; Free's card leads to the cancel sheet |
| Anyone, Enterprise | **Contact us** | Unchanged |

A cancelled Checkout returns to where it started: the pricing page at `/pricing?plan=…&billing=…&checkout=canceled` with the choice still selected and "Checkout canceled — you weren't charged.", or Billing with "Checkout was canceled. Nothing was charged." when the dashboard started it.

**Billing settings (dashboard).** Billing moves to its own `/settings/billing` tab; `/settings/general` keeps a one-line plan summary that links to it.

```text
Billing
┌─────────────────────────────────────────────────────────────────┐
│ Premium · Monthly                                 [ Change plan ]│
│ $14.99/month · Renews Nov 3, 2026 · Visa •••• 4242               │
│ ──────────────────────────────────────────────────────────────── │
│ Pay yearly: $143.88/yr instead of $179.88 — save $36.00 a year.  │
│                                              [ Switch to yearly ]│
└─────────────────────────────────────────────────────────────────┘
┌ Scheduled ──────────────────────────────────────────────────────┐
│ Changes to Premium · Monthly on Oct 17, 2027.  [ Keep current ] │
└─────────────────────────────────────────────────────────────────┘
Usage                                  (today's usage overview)
Plans                 ┌ Monthly │● Yearly ┐
 Free · Premium (● Current) · Growth · Organization · Enterprise
Payment & invoices    Visa •••• 4242 · Billing history   [ Manage ↗ ]
Cancel subscription
```

The "Pay yearly" line appears only on a monthly plan. The Scheduled panel appears only when a change or cancellation is pending. The plan row shows every tier, current and lower ones included, with the same price presentation as the pricing page.

**Change sheet: upgrade or switch to yearly.**

```text
┌ Switch to Premium · Yearly ────────────────────────────────┐
│ Premium · Monthly  →  Premium · Yearly                      │
│ Starts today. Your features stay the same.                  │
│                                                             │
│ Due today                                         $133.89   │
│   Premium · Yearly (1 year)                       $143.88   │
│   Credit for unused time this month               −$9.99    │
│ Then $143.88/year, next on Oct 17, 2027                     │
│ Charged to Visa •••• 4242                                   │
│                                                             │
│ [   Pay $133.89 and switch   ]              Not now         │
│ Unused time is always credited — you never pay twice.       │
└─────────────────────────────────────────────────────────────┘
```

A tier upgrade adds a "What you get" block: `Ledgers 5 → 20 ↑ · AI tokens 500K → 2M ↑ · Automation & integrations ✓`. Both sheets list the same rows as the pricing table: the limits, from the preview's `limitChanges`, and the plan features, from the pricing table's feature rows (question 21, item 6).

**Change sheet: downgrade or switch to monthly.**

```text
┌ Downgrade to Premium ──────────────────────────────────────┐
│ Growth · Yearly  →  Premium · Yearly                        │
│ Starts Oct 17, 2027. You keep Growth until then.            │
│ Nothing to pay today. Then $143.88/year.                    │
│                                                             │
│ What changes on Oct 17, 2027                                │
│   Ledgers                   20 → 5     you have 12  ⚠       │
│   Collaborators / ledger    10 → 5                          │
│   AI tokens / month         2M → 500K                       │
│   Automation & integrations  ✓ → —                          │
│                                                             │
│ ⚠ All 12 ledgers stay yours and keep working. You can't     │
│   create a new one until you have fewer than 5.             │
│                                                             │
│ [  Schedule downgrade  ]                    Keep Growth     │
└─────────────────────────────────────────────────────────────┘
```

**Change sheet: higher tier while leaving yearly.** The sheet offers both options rather than picking one:

```text
Growth monthly can start at your renewal on Oct 17, 2027.
Want Growth today?
  ( ) Get Growth today on yearly billing — about $408 now
  ( ) Switch to Growth monthly on Oct 17, 2027 — nothing today
```

The amount is illustrative: Premium yearly with six months left, so half of $959.88 less half of $143.88. The real figure comes from the preview.

**Bank authentication.** When the backend reports that authentication is required, the sheet runs Stripe.js confirmation in place. If it succeeds, the sheet goes to the success state. If it fails, the sheet says "Your bank didn't approve the payment. Nothing changed." with **Try again** and **Use another card ↗**. If Stripe.js is unavailable, the sheet falls back to the invoice's hosted payment page. A toast that sends the customer to their email is never the outcome.

**After Checkout.** `success_url` becomes `/settings/billing?checkout=success&session_id={CHECKOUT_SESSION_ID}`, which polls until the webhook has recorded the subscription:

```text
① ◌ Confirming your payment…
② ✓ You're on Premium · Yearly
    Renews Oct 17, 2027 for $143.88. Receipt sent to you@example.com.
    Now unlocked: 5 ledgers · 5 collaborators · 500K AI tokens/mo ·
    unlimited entries
    [ Back to “Household 2026” ]          View billing
③   Payment received. Your plan will appear in a minute —
    we'll email you when it's active.     [ Refresh ]
```

State ③ appears if about 20 seconds pass without the webhook. It is never styled as an error, because the customer has paid. **Back to …** uses a `return` parameter validated by `getSafeRedirectPath`, so the customer lands where the upgrade began.

**Cancel sheet.**

```text
┌ Cancel Premium? ───────────────────────────────────────────┐
│ You keep Premium until Nov 3, 2026. Then you're on Free:    │
│   1 ledger · 1 collaborator · 1,000 entries · 20K tokens    │
│ Your books are plain text — export anytime. Nothing is      │
│ deleted.                                                    │
│ Other options                                               │
│   [ Switch to yearly — $11.99/mo ]   (monthly plans only)   │
│   [ Downgrade to Premium ]           (Growth and above)     │
│ What's the main reason? (optional)                          │
│   ○ Too expensive  ○ Missing a feature  ○ Not using it      │
│   ○ Switching tools  ○ Other                                │
│ [  Cancel subscription  ]                   Keep Premium    │
└─────────────────────────────────────────────────────────────┘
```

After cancelling, the Scheduled panel reads "Premium ends Nov 3, 2026 — [Resume]".

**Failed renewal.** A banner on every dashboard page: "We couldn't charge Visa •••• 4242 for Premium. Update it by Nov 10 to keep Premium. [Update payment method]". The date is Stripe's last scheduled retry (question 21).

**Older prices.** A subscriber on an older Premium price — $9.99 a month or $99.99 a year — sees it labelled, for example "Premium · Monthly · $9.99 (legacy price)". Every change sheet for that subscriber adds: "Your legacy price ends with this change. You can't switch back to it."

**In-product prompts.** The AI Assistant panel, the ledger-limit nudge and the usage nudges deep-link to a prefilled sheet instead of the general settings page, for example:

```text
/settings/billing?plan=growth&billing=yearly&from=ledger_limit&return=/ledger/alice/books
```

The prompt recommends the next tier for a ledger or collaborator limit. For AI tokens, it recommends the lowest tier whose allowance covers the current usage. Subscriber CTAs on the pricing page use the same link shape, tagged with new stable attribution campaign ids.

### 16. What does the backend need?

Three GraphQL operations and two status fields:

```graphql
previewPlanChange(clientId: String!, priceId: String!): PlanChangePreview!
  # kind: UPGRADE | TO_YEARLY | DOWNGRADE | TO_MONTHLY | SPLIT
  # effectiveAt, amountDueToday, creditApplied, nextAmount, nextChargeAt,
  # prorationDate, limitChanges, paymentMethod { brand, last4 },
  # replacesScheduledChange, withdrawsCancellation

changePlan(clientId: String!, priceId: String!, prorationDate: DateTimeISO): PlanChangeResult!
  # status: ACTIVE | REQUIRES_ACTION | SCHEDULED | FAILED
  # clientSecret, hostedInvoiceUrl, effectiveAt, message

cancelScheduledPlanChange(clientId: String!): SubscriptionActionResult!

# Subscription gains: scheduledChange { priceId, effectiveAt }, paymentMethod
```

- **Preview** uses Stripe's invoice preview (`invoices.createPreview`) with the subscription's items and a fixed proration time. It returns that time so `changePlan` charges what the customer saw.
- **Immediate changes** keep today's `upgradeSubscription` mechanics (`always_invoice`, `pending_if_incomplete`), with `proration_date` from the preview. `latest_invoice` must be expanded, and authentication is read from the invoice's payments, not from `payment_intent` (question 13).
- **Scheduled changes** use a Subscription Schedule created from the subscription: the current phase runs to period end, and the next phase holds the new price. `cancelScheduledPlanChange` releases the schedule. A cancellation and a scheduled change are mutually exclusive, and the preview says which one a new choice replaces.
- **Status** passes `past_due` through, and tier resolution keeps paid limits for `past_due` until Stripe's last scheduled retry. Tier resolution should also stop treating an unreachable Stripe as Free: `getUserTier` returns `FREE` on any lookup error (`backend-cluster/backend-v2/src/features/stripe/operations/get-user-tier.ts`), so a Stripe outage applies Free limits to every subscriber.
- **Limit checks** get the two fixes in question 21, item 6: the ledger count covers every ledger the owner owns, and the collaborator limit uses the ledger owner's plan and the resource-limit error.
- `upgradeSubscription` remains until no client calls it, then follows the normal deprecation path.

These are self-service billing operations, so they follow [the authorization model](../../backend-cluster/backend-v2/authz/README.md#self-service-billing):

- Each operation gets its own action in the catalog, and is browser-session-only like the five existing billing mutations.
- Each passes the resolved `Identity` to `SubscriptionService` for one PDP call before touching Stripe.
- Each is registered in the parity baseline with no REST or MCP eligibility, matching today's billing aliases under the [API parity requirements](../../backend-cluster/backend-v2/AGENTS.md#required-api-parity-workflow).

### 17. What changes in Stripe configuration?

- **Customer portal:** a dedicated configuration, passed as `configuration` on every portal session. It allows payment-method updates, invoice history and billing address or tax ID, and disables subscription update and cancellation. All plan changes then go through question 14's rules, and no price outside `SUBSCRIPTION_CONFIG` can be reached.
- **Checkout:** a `success_url` and a `cancel_url` built per session as in question 15, instead of the static marketing-page URLs. Promotion codes stay enabled.
- **Prices:**
  - Create the $143.88 Premium yearly price in the live account, and point the backend `SUBSCRIPTION_CONFIG`, the dashboard `stripe-config.ts` and the pricing page's checkout at it for new subscriptions.
  - Keep the $99.99 price in `SUBSCRIPTION_CONFIG` so existing yearly subscribers still resolve to Premium.
  - Confirm every configured price is active before stage 1 ships.
- **Pricing-page copy:** the page's structured price data and its FAQ answer quoting "$8.33 per month billed annually" must change in every locale.
- **Email:** keep Stripe receipts, and enable Stripe's upcoming-renewal reminder for yearly plans. Beancount.io sends its own email when a plan change is scheduled, and seven days before it takes effect.

### 18. What ships in each stage?

| Stage | Customer outcome | Evidence required to advance |
| --- | --- | --- |
| 1. Yearly reachable | Premium's $143.88 yearly price on every surface; yearly as the pricing page's default; Growth as most popular on both surfaces; Billing tab with the cycle toggle and **Switch to yearly**; upgrade and to-yearly previews; in-place bank authentication; the post-Checkout confirmation; prefilled deep links from the pricing page and in-product prompts; visible pricing-page errors; the pinned portal configuration | Every configured price confirmed active, and a new Premium yearly checkout charges $143.88; against synthetic fixtures and mocked Stripe responses (no live purchase), a preview equals the resulting invoice for each immediate change kind, a payment requiring authentication completes in place, and a declined one leaves the plan unchanged; a monthly subscriber reaches yearly from the pricing page and from Billing |
| 2. Downgrades and recovery | Scheduled downgrades and switches to monthly, undo, replacement and the split choice; the ledger-count and collaborator-limit fixes; the cancel sheet's alternatives and reason; paid limits kept through Stripe's retries, and the failed-payment banner; scheduled-change emails | Each row of question 14 exercised against synthetic fixtures and mocked Stripe responses through its effective date; the limits shown in the downgrade sheet match what the backend enforces afterwards (question 21, item 6) |
| 3. Growth experiments | Placement of the "Pay yearly" line; renewal reminder copy | Stage 1 and 2 metrics have a baseline of at least four weeks |

### 19. How do we know whether it worked?

New analytics events, alongside today's `checkout_started` and a `purchase` sent from the browser once per paid invoice (the confirmation after Checkout, or the change sheet after an upgrade that charged; it replaced a server-side Measurement Protocol event on 2026-10-20):

- `billing_toggle_changed {to, surface}`
- `plan_change_previewed {kind, from, to, surface}`
- `plan_change_confirmed`, `plan_change_scheduled`, `plan_change_reverted`
- `payment_action_required`, `payment_action_failed`
- `cancel_started`, `cancel_confirmed {reason}`, `subscription_resumed`

| Measure | Today |
| --- | --- |
| Yearly share of new and changed subscriptions started from the dashboard | Zero by construction (question 13) |
| Monthly-to-yearly switches by existing subscribers per month | No path exists |
| Downgrades ÷ (downgrades + cancellations) | No downgrade path exists |
| `checkout_started` → `purchase` completion | Not measured |
| Preview → confirm rate per change kind; authentication failure rate | Not measured |

None of these are measured today. Revisit the design if yearly adoption from the dashboard stays near zero after stage 1. Revisit the cancel sheet if cancellations rise after stage 2, or if alternatives are taken and then reverted within a cycle. With yearly as the default, `billing_toggle_changed` shows how many visitors switch to monthly before checkout.

### 20. What is out of scope?

- New tiers, and any price change other than Premium yearly.
- Mobile billing.
- Per-seat or quantity pricing.
- Currencies other than USD.
- Sales tax.
- Trials.
- Discounts outside Checkout promotion codes.
- Any change to the tier limits themselves.
- How the pricing table's on-request features (automatic backups, automation & integrations, OIDC SSO, multi-entity consolidation) are provided.

### 21. What has been decided?

Decided on 2026-10-17:

1. **Failed renewals follow Stripe's current retry schedule.** A `past_due` subscriber keeps paid limits until Stripe's last scheduled retry, and the banner's date is that retry. There is no extra grace beyond it.
2. **Yearly is the pricing page's default cycle.** It ships in stage 1 rather than as an experiment.
3. **Premium yearly costs $143.88 a year ($11.99 a month), a 20% saving like every other tier.** It applies to new Premium yearly subscriptions. Subscribers on the $99.99 price keep it under question 11's rules. Every tier now saves 20%, so the toggle says "save 20%".
4. **No refunds.** Plan changes credit unused time against the new charge; nothing is refunded (question 12).
5. **Growth is the most popular plan** on the pricing page and in the dashboard. The pricing page's badge moves from Premium (defect 9).
6. **What a downgrade does to each limit.** Nothing is deleted; each limit only stops the customer adding more, and plan features follow the pricing table, as question 5 says. Per limit:

   - **Ledger count** (Free 1 · Premium 5 · Growth 20 · Organization 100)
     - *Rule:* checked only when a ledger is created, against the owner's plan (`backend-cluster/backend-v2/src/features/ledger/operations/create-ledger.ts:89`). Existing ledgers are never touched. After a downgrade every ledger keeps working, and creating one fails until the owner is under the new limit.
     - *Bug, fixed in stage 2:* the check counts the owner's ledgers among only the first 10 the ledger service returns (`limit: 10`, `:75`), so it can never fire at Growth's or Organization's limit. It must count every ledger the owner owns.
     - *Intended:* ledgers created from the mobile app skip the check (`platform !== "mobile"`, `:71`).
   - **Collaborators per ledger** (1 · 5 · 10 · 50)
     - *Rule:* checked only when a new collaborator is added, against the **ledger owner's** plan. Existing collaborators keep their access, and permission changes are never refused. After a downgrade, adding someone fails while the ledger is at or over the owner's new limit.
     - *Bug, fixed in stage 2:* today the check uses the plan of whoever adds the collaborator (`backend-cluster/backend-v2/src/features/ledger/workflow/ledger-collaborators-workflow.ts:136–156`), so an admin collaborator on another plan gets that plan's limit. The same fix replaces the internal server error that always says "Upgrade to PREMIUM" with the resource-limit error ledger creation uses, naming the owner's plan.
   - **Entries on Free** (1,000; every paid tier is unlimited)
     - *Rule:* two enforcement points, both of which allow the write if the count or the tier lookup fails:
       - A write through Beancount.io (dashboard or API, via ledger-v2's entry and file endpoints) is refused when it would leave the ledger over the cap *and* make it bigger. Edits and deletions always work (`backend-cluster/ledger/src/core/directive-limit.ts`).
       - A `git push` through the git proxy is refused whenever the ledger is already over the cap, even if the push would shrink it, because the proxy can't count a pack before it lands. A push that crosses the cap still lands, and the next one is refused (`backend-cluster/backend-v2/src/features/gitea/policy/directive-limit-gate.ts`).
     - After a downgrade the ledger stays readable, and the owner gets back under 1,000 by deleting entries in the dashboard.
     - *Intended:* writes from the mobile app are exempt (`backend-cluster/backend-v2/src/features/ledger/operations/directive-limit-bypass.ts`).
     - The pre-receive hook described in `backend-cluster/idl/beancount-ledger.openapi.json` was removed on 2026-08-20; that description is stale.
   - **API keys** (paid tiers only)
     - *Rule:* creating a key requires a paid tier (`backend-cluster/backend-v2/src/foundation/composition/builder.ts:82`). Existing keys keep working on Free, and the refusal message says so. The downgrade sheet mentions it.
   - **Features in the pricing table** (automatic backups, advanced automation & integrations, OIDC SSO, multi-entity consolidation)
     - *Rule:* left as they are. These features exist and are provided on request to the plans the pricing table lists them under, which is why backend-v2 has no tier check for them. None is added. The change sheets show them exactly as the pricing table does, gained on an upgrade and removed on a downgrade (question 15).
   - **AI Assistant tokens** (20K · 500K · 2M · 10M a month)
     - *Rule:* checked before every request against the current plan, and counted per calendar month in UTC, not per billing period (`backend-cluster/backend-v2/src/features/feature-usage/service/feature-usage-service.ts`).
     - *Intended:* a downgrade that takes effect mid-month counts the month's earlier usage against the lower allowance, so a customer already past it is paused until the first of the next month (question 5).

No decisions remain open.
