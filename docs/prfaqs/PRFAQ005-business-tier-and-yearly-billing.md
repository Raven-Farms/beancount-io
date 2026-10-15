# PRFAQ005 — Business Tier and Yearly Billing

Status: Research-backed proposal for review; no product or pricing changes implemented

Date: 2026-10-09 (America/Los_Angeles)

Scope: A new **Business** subscription tier for owner-operated companies, a **Practice** naming and ledger-pack extension for accounting firms, and a fix that lets any subscriber choose **yearly billing** from inside the product, not only from the marketing pricing page.

Evidence baseline: `beancount-io` commit `42572c82` and the CMS repository on 2026-10-09, both read-only; the published customer research [Who is hosted Beancount really for?](https://beancount.io/blog/2026/10/08/who-is-hosted-beancount-really-for); competitor list prices checked on 2026-10-08. No customer interviews have been run for this proposal and no conversion or revenue effect is measured or implied.

**Recommendation:** Add a Business tier at $29.99 a month or $287.88 a year, rename Growth to Practice and add a 50-ledger Practice pack, keep every existing subscriber on their current price and limits, and ship a yearly-billing toggle in the dashboard's subscription settings in the same release. Validate the price and the Business feature set with the sign-up segmentation question and three customer interviews before the public launch; the yearly-billing fix needs no validation and can ship first.

This builds on the quota model documented in the backend's `TIER_LIMITS` and on the evidence-preservation stance of [PRFAQ001](PRFAQ001-ledger-creation.md): nothing here changes what a ledger is or who owns it. It is a proposal about who the plans are for and how they pay.

## Why now

The customer research in [Who is hosted Beancount really for?](https://beancount.io/blog/2026/10/08/who-is-hosted-beancount-really-for) shows that most people paying for hosted Beancount keep business books and compare it with QuickBooks, not with running Fava themselves.

The product does not yet speak to them:

- The plan most of them are on is labelled **Personal Finance** on the pricing page. A company buys a plan whose name tells them they are in the wrong place.
- The jump from that plan to the next is **$14.99 to $99.99 a month**, with nothing between. A one-company business has no plan priced for a one-company business.
- An accountant trialling the product for clients has no plan named for a practice, no per-client economics, and no way to tell which tier to recommend.
- **Yearly billing exists only on the marketing page.** The pricing page has a monthly/yearly toggle and starts a yearly checkout for a signed-in user without a subscription; the dashboard's subscription settings start every new or upgraded subscription on the monthly price (`dashboard/src/features/user-settings/pages/general/subscription-section.tsx:150` and `:171`), and the pricing page sends an existing subscriber to those settings. A current monthly subscriber therefore has no in-product path to an annual plan, even though the pricing FAQ promises one on every paid tier.

## Press release

*Proposed launch copy, written as if released. Names, prices and availability remain proposals; this is not a current product announcement.*

**Beancount.io introduces a Business plan for companies that want books they own, and lets every subscriber pay yearly**

*Real books for a small company, readable by your accountant, on a plan that is finally named for you.*

Beancount.io today introduced the **Business** plan for owner-operated companies that keep their own books and want to leave the subscription treadmill behind. Business gives a company up to five ledgers, five collaborators on each ledger, invoice billing, an accountant hand-off package, a year-end close archive and priority support, for $29.99 a month or $287.88 a year.

Until today the people keeping company books on Beancount.io were buying a plan called Personal Finance, because it was the only one priced for a small company. Business changes the name, the limits and the features to match what they actually came for: a set of books that is correct, that their accountant can read line by line, and that stays theirs as a plain-text file no matter what happens to the software.

The accountant hand-off package produces the two reports a tax preparer asks for at year end, a trial balance and a general-ledger detail, as a dated bundle the owner can send without exporting anything by hand. The year-end close archive freezes a tax year's books and reports at a point in time, so a question in a later audit can be answered from the records as they were, not as they are today. Invoice billing lets a company pay the way companies pay.

For accounting and bookkeeping firms, the Growth plan is now called **Practice** and keeps its 20 ledgers at $99.99 a month, with a new **Practice 50** pack at $199.99 a month. A firm can run its own books and its clients' books in one workspace, and a client can also keep paying for their own Business plan and simply invite the firm as a collaborator. Both routes work today; the plans now say so.

Every paid plan can be billed yearly from inside the product. The subscription settings page now offers monthly or yearly at checkout and at upgrade, and the pricing page's yearly selection carries through sign-up and into the dashboard. Yearly billing on Business and Practice is priced at ten months for twelve.

Existing subscribers keep their current plan, price and limits for as long as they stay subscribed. Nothing moves without the customer choosing it.

## Customer FAQ

### 1. I run a small company. Which plan is for me, and what do I get that I don't have today?

**Business.** Today a company either buys the Personal plan, which fits a household, or jumps to a plan priced for twenty ledgers. Business is priced for one company and adds four things no current plan has:

| | Personal | Business |
| --- | --- | --- |
| Ledgers | 3 | 5 |
| Collaborators per ledger | 2 | 5 |
| AI Assistant tokens | 500K | 1M |
| Pay by invoice | No | Yes |
| Accountant hand-off package | No | Yes |
| Year-end close archive | No | Yes |
| Priority support | No | Yes |
| Multi-currency, investments, importer, backups, mobile | Yes | Yes |

Three of those rows are limits and take effect the day the plan exists. Three are features that must be built before launch; see Internal FAQ 12. The Personal limits above apply to **new** Personal sign-ups; see FAQ 6 for what happens to anyone already subscribed.

### 2. Why does a company need five collaborators?

Because company books are rarely one person's. The owner records, a bookkeeper categorizes, the accountant reviews at quarter end, and a partner or spouse wants to see the balance sheet. Collaborators are counted per ledger, so a company with two ledgers can give each its own set of five. A household is two people; the Personal limit reflects that.

### 3. What is the accountant hand-off package, and why would my accountant want it?

Most accountants work in QuickBooks or Xero and will not learn Beancount for one client. They do not need to. What they ask for at year end is a **trial balance** as of the closing date and a **general-ledger detail** listing every posting grouped by account. The package produces both as PDF and CSV for a chosen period, stamped with the ledger revision it came from, so the figures in the PDF can be traced back to the exact lines in the file.

Today a technical owner can produce the same two reports with `bea query`, and the tax-preparation guide walks through it. The package removes the step for owners who are not technical, which the research says is most new business sign-ups.

### 4. What does the year-end close archive do?

It records the state of a tax year's books and reports at the moment you close it. In a plain-text ledger that is a tagged revision plus the frozen reports. If a question comes two years later, you answer it from the books as they stood when the return was filed, not from books that have since been corrected or reclassified. Nothing is locked: the live ledger stays editable, and a later correction is visibly later.

### 5. I am an accountant or bookkeeper. Which plan do I buy, and how do my clients pay?

There are two routes, and both already work mechanically; the plans now name them.

- **Clients pay.** Each client subscribes to Business and invites you as a collaborator. You pay nothing for that client. This matches how most small clients already pay for their own QuickBooks subscription.
- **The firm pays.** You subscribe to **Practice** (20 ledgers, $99.99 a month) or **Practice 50** (50 ledgers, $199.99 a month), create a ledger per client, and set your own fee. Your firm's own books count as one of the ledgers. A client can be invited to their ledger as a collaborator at no extra cost.

The per-ledger cost on Practice is $5.00 a month at 20 ledgers and $4.00 at 50. For comparison on 2026-10-08, QuickBooks Ledger, the accountant-only plan for low-activity clients, listed at $10 a month per client, and Xero Ledger at $4 per client.

### 6. I already pay for Premium or Growth. Does anything change for me?

No. Your plan keeps its name on your invoice, its price and its limits for as long as you stay subscribed, including the five ledgers and five collaborators on today's Premium. The new Personal limits apply only to people who sign up after the change. You can move to Business or Practice if you want what they add; nobody is moved for you.

### 7. I pay monthly. Can I switch to yearly without cancelling?

Yes, and this is the part of the release that fixes something broken today. The subscription settings page gains a monthly/yearly choice for new subscriptions and for upgrades. Switching an existing monthly subscription to yearly is a plan change with the unused part of the current month credited, which is how upgrades between tiers already work in the backend.

Today the only yearly checkout is on the public pricing page, and it is only offered to a signed-in user who has no subscription yet. If you already subscribe, that page sends you to the settings page, which only knows the monthly price. The FAQ on the pricing page says every paid plan offers annual billing; after this release that is true everywhere, not only on the pricing page.

### 8. How much does yearly save?

| Plan | Monthly | Yearly | Per month on yearly | Months free |
| --- | --- | --- | --- | --- |
| Personal | $14.99 | $99.99 | $8.33 | about 5.3 |
| Business | $29.99 | $287.88 | $23.99 | 2.4 |
| Practice | $99.99 | $959.88 | $79.99 | 2.4 |
| Practice 50 | $199.99 | $1,919.88 | $159.99 | 2.4 |
| Organization | $499.99 | $4,799.88 | $399.99 | 2.4 |

Personal keeps its existing yearly price, which is a steeper discount than the others; changing it is out of scope here. Business and Practice follow the Growth and Organization convention of a monthly figure multiplied by twelve.

### 9. Why would I pay $29.99 for Business when Personal is $14.99 and has most of the same features?

If you keep a household's books, you should not. Personal is the right plan and nothing is being taken from it. Business is for a company, and the price buys the things a company needs and a household does not: invoice billing, the hand-off package, the archive and a response when something is wrong during a close. On 2026-10-08 the QuickBooks Online plan that allows three users listed at $85 a month; Business allows five collaborators per ledger at about a third of that and leaves the books in a file you own.

### 10. Can I take my books with me if I cancel?

Yes, exactly as before. Your ledger is a plain-text file; export it any time and keep working with the open-source Beancount tools. No plan, including Business and Practice, changes that. The archive bundles and hand-off packages you generated remain yours as files too.

### 11. I am in Canada or outside the US. Is anything different?

Prices are in US dollars on every plan, as today. Invoice billing works for any company Stripe can invoice. Canadian GST/HST bookkeeping is covered by a new guide in the documentation rather than by a plan feature. Local-currency pricing is not part of this proposal.

## Internal FAQ

### 12. What has to be built, and what is configuration?

The tier system is smaller than it looks. A user's tier is **derived at request time from the Stripe price on their subscription**, matched against `SUBSCRIPTION_CONFIG.plans` (`backend-cluster/backend-v2/src/features/stripe/operations/get-user-tier.ts`), and every limit is one of four numbers per tier in `TIER_LIMITS` (`.../stripe/service/stripe.ts`). Nothing is stored in the database.

| Change | Kind | Where |
| --- | --- | --- |
| New enum values `PERSONAL`, `BUSINESS`, `PRACTICE_50`; `GROWTH` keeps its value and gains the display name Practice | Configuration | `stripe.ts` `SubscriptionTier`, `TIER_LIMITS` |
| Two Stripe prices per new tier per environment, each tagged with its tier | Configuration plus Stripe console | `SUBSCRIPTION_CONFIG` `plans`, `planIds`, `productIds`; dashboard `stripe-config.ts`; CMS `stripe.ts` and `stripe-prices.ts` |
| Dashboard tier table and labels in 16 locales | Configuration | `tier-config.ts`, `use-user-limits.ts`, `features/ai-agent/locales/*.ts` |
| Pricing page: columns, feature rows, JSON-LD offers, FAQ copy in 16 locales, grid CSS for seven columns | Configuration and copy | CMS `pricing-data.ts`, `pricing-jsonld.ts`, `PricingSection.tsx`, `pricing.css`, `i18n/*/pricing.json` |
| Yearly toggle in subscription settings; `?billing=yearly` deep link honoured | Small feature | `subscription-section.tsx`, `subscription-upgrade-cards.tsx` and their tests |
| Pay by invoice on Business and above | Small feature | Stripe Checkout payment methods and customer portal settings; today invoice payment is listed for Enterprise only |
| Accountant hand-off package | Feature | New: dated trial balance plus general-ledger detail as PDF and CSV, stamped with ledger revision; the reports exist via `bea query` |
| Year-end close archive | Feature | New: tag a revision and freeze its reports for a tax year |
| Priority support | Process | Support routing by tier |

The yearly toggle can ship on its own first: the yearly price IDs already exist in every config, and `upgradeSubscription` accepts any configured price with `proration_behavior: "always_invoice"` (`stripe-service.ts:303-305`).

### 13. How does grandfathering work without a migration?

Because the tier comes from the price ID, the old Premium prices continue to resolve to `PREMIUM` with its five-ledger, five-collaborator limits, and the new Personal prices resolve to `PERSONAL` with the new limits. The enum value *is* the grandfather list. The same holds for Growth: the existing price IDs keep their 20 ledgers under the name Practice. No subscriber record is touched, and the pricing page stops selling the old Premium price on launch day.

### 14. Why not price Practice per ledger instead of in packs?

Checkout and upgrade send a single price with `quantity: 1`, and limits are fixed per tier. Metered or quantity-based billing would be a new mechanism in the backend, the dashboard and the quota checks. Packs of 20 and 50 are two more rows in the same tables and give the firm a predictable bill. Revisit per-ledger billing if a firm regularly needs more than 50 ledgers and Organization does not fit.

### 15. Why can Business not be distinguished by ledger count alone?

Ledgers have no type. A one-person company needs one ledger; a household may keep three. The honest differentiators are collaborators and company features, and three of the Business rows are features that do not exist yet. A Business column whose only difference from Personal is a bigger token number would be a label, not a plan, and the research says these buyers compare feature rows against QuickBooks.

### 16. What do competitors charge, and where does this sit?

List prices observed on 2026-10-08, US dollars per month:

| Product | Entry | Mid | Accountant channel |
| --- | --- | --- | --- |
| QuickBooks Online | $38 (1 user) | $85 (3 users) | QuickBooks Ledger $10 per client; firm-billed 30% discount for the life of the subscription; firm software free |
| Xero | $27 (invoice caps) | $59 | Partner program free; Xero Ledger $4 and Cashbook $10 per client |
| Wave | $0 | Pro $19 per business | Bank feeds and accountant access require Pro since June 2026 |
| FreshBooks | $23 | $43 | $11 per extra user |
| Puzzle | $30 | $72 | Quote-based for firms |

Business at $29.99 sits beside Xero's and Puzzle's entry plans and well under the QuickBooks plan that allows three users, while offering five collaborators. Practice at $5.00 a ledger matches Xero's partner-only Ledger plan and is half of QuickBooks Ledger. Wave's move to gate accountant access behind a paid plan is independent evidence that "your accountant can get in" is something customers pay for.

Prices in this table are third-party and vendor pages read on one day; confirm before publishing any comparison.

### 17. What must be true before the public launch?

The yearly fix has no precondition. For the tiers:

- The sign-up question *personal, my business, or my clients' books?* is live in the product and the CMS attribution report groups CTA surfaces by audience segment, so the share of business sign-ups is measured rather than inferred.
- Three customer interviews from the research sample, two accountants and one non-technical owner, have answered four questions: what they pay QuickBooks today, who else touches the books, what "accountant-ready" means to them, and whether per-client pricing is acceptable.
- At least two of the three Business features are built and tested, so the Business column differs from Personal in more than numbers.
- Stripe products and prices exist in live and test mode, the customer portal configuration permits switching between the new prices, and the CMS and backend configurations ship together; a pricing page that sells a price the checkout does not accept is the failure mode to avoid.
- Existing subscribers have been told in writing that nothing changes for them.

### 18. How do we know whether it worked?

Provisional measures, to calibrate once the segmentation question has eight weeks of data:

- Share of new paid subscriptions on Business among sign-ups that answered *my business*; a majority choosing Personal means the Business column is not persuading and the limits or features need another look before the price does.
- Yearly share of new and upgraded subscriptions from the dashboard, which is zero today by construction.
- Monthly-to-yearly switches by existing subscribers in the first 90 days.
- Practice subscriptions and the median ledgers per Practice account, which tells us whether 20 and 50 are the right packs.
- Churn on Personal versus Business over the first two quarters, read against the seasonal pattern tax-driven businesses show.

None of these are measured today. Stop and reconsider if business sign-ups keep choosing Personal, if yearly adoption in the dashboard stays near zero after the toggle ships, or if the three Business features cannot be built within one release.

## Feature inventory — verified 2026-10-11

Read-only inspection of `beancount-io` (`42572c82`) and the CMS. 🟢 exists and is enforced or shipped · 🟡 the ingredients exist but not the customer-facing feature, or the behaviour is unverifiable from code · 🔴 nothing in either repository.

### Business tier rows

| Row | Status | Evidence |
| --- | --- | --- |
| Ledger, collaborator, entry and AI-token limits per tier | 🟢 | `TIER_LIMITS` in `stripe/service/stripe.ts`, enforced in `ledger/operations/create-ledger.ts`, `ledger/workflow/ledger-collaborators-workflow.ts`, `ledger/operations/directive-limit-lookup.ts`, `feature-usage/service/ai-cfo-usage-service.ts` |
| Pay by invoice | 🔴 | No `collection_method`, `send_invoice` or invoice payment path in backend or dashboard; the pricing page lists it for Enterprise, so it is handled outside the product today |
| Accountant hand-off package | 🟡 | Reports exist in `dashboard/src/features/reports` (trial balance, income statement, balance sheet, cash flow, account); `StatementExportMenu` offers CSV and browser print on income statement, balance sheet and cash flow, with a `generatedAt` stamp, but not on trial balance; journal exports a `.beancount` file; BQL results export CSV. Missing: a general-ledger detail report, a one-click dated bundle, a ledger-revision stamp, generated PDF |
| Year-end close archive | 🟡 | Ledgers are Gitea repositories with a commit history and pull-request UI (`dashboard/src/features/git`); `GET /api-gateway/v1/ledgers/{owner}/{name}/archive/{archive}` streams a branch zip or tarball; ledger options carry `fiscalYearEnd`. The generated Gitea client has `repoCreateTag`/`repoListTags` but no product code calls them. Missing: a close action, a tag per tax year, frozen reports |
| Priority support | 🔴 | No support routing, tier flag or vendor integration in either repo |
| Multi-currency, investments | 🟢 | Beancount core; holdings and commodity price history in `ledger-data` |
| Smart Import (CSV, PDF, OFX, images) | 🟢 | `dashboard/src/features/importer`, paid-tier gated via `isPremiumRequired` |
| Automatic backups | 🟡 | Pricing page row; only self-hosting READMEs mention backups. Hosted ledgers live in Gitea, so history is inherent, but an off-site backup of the hosted service is not verifiable from the repositories |
| Mobile app sync | 🟢 | `beancount-mobile` OAuth client in `oauth/data/config.ts`; iOS and Android apps |

### Practice rows

| Row | Status | Evidence |
| --- | --- | --- |
| Practice 20 | 🟢 | Exists today as Growth: 20 ledgers, 10 collaborators per ledger, 2M tokens |
| Practice 50 | 🔴 | One `TIER_LIMITS` row and two Stripe prices per environment; nothing exists yet |
| Firm workspace: every client ledger in one list | 🟡 | The dashboard sidebar lists own and shared ledgers with an owner line (`ledger-list/pages/dashboard-page/components/dashboard-sidebar.tsx`); there is no firm or client grouping, no per-client summary |
| Invite a client or an accountant to a ledger with read, write or admin rights | 🟢 | `dashboard/src/features/collaboration`, `CollaboratorPermissionType = "read" \| "write" \| "admin"`; limit enforced per ledger by tier |
| Client-billed and firm-billed routes | 🟢 | Mechanically present: whoever subscribes owns the ledgers; the other party is a collaborator at no cost |
| Accountant revenue share | 🟡 | The CMS affiliate programme pays 20% recurring for up to 12 months; no accountant-specific rate or sign-up |

### Yearly billing

| Row | Status | Evidence |
| --- | --- | --- |
| Yearly price IDs for every paid tier in both environments | 🟢 | CMS `src/config/stripe.ts`; backend `SUBSCRIPTION_CONFIG`; dashboard `stripe-config.ts` |
| Yearly checkout from the pricing page for a signed-in user with no subscription | 🟢 | `PricingSection.tsx` toggle and `handleTierCheckout` (`plan.yearly.priceId`) |
| `?billing=yearly` carried through sign-up back to the pricing page | 🟢 | `pricingSignupUrl` in `PricingSection.tsx` |
| Yearly choice in the dashboard for a new subscription or an upgrade | 🔴 | `subscription-section.tsx:150` and `:171` pass `stripeConfig[tierKey].monthly`; upgrade cards show the monthly price only; `?billing=yearly` is not read |
| Switch an existing monthly subscription to yearly | 🟡 | Backend `upgradeSubscription` accepts any configured price with `proration_behavior: "always_invoice"` (`stripe-service.ts:303-305`); no UI offers a yearly price to an existing subscriber |
| Switch cadence in the Stripe customer portal | 🟡 | `stripe.billingPortal.sessions.create` is called without a `configuration` (`stripe-service.ts:724`), so this depends on the default portal settings in the Stripe console, which the code cannot show |

### Rows the pricing page already advertises

These must be reconciled before the matrix is redrawn; the first three are claims the code does not currently back.

| Row | Status | Evidence |
| --- | --- | --- |
| OIDC single sign-on (Organization and Enterprise) | 🟡 | Beancount.io is an OAuth 2.0 / OIDC **provider** for its own mobile app, the Discourse forum and third-party clients (`features/oauth`). No path lets a company sign in to Beancount.io with its own identity provider; `auth-service.ts` has email, password and OTP only. As a buyer reads the row, it is not implemented |
| Multi-entity consolidation (Organization and Enterprise) | 🔴 | No consolidation feature in backend or dashboard; the only matches are an unrelated Fava helper and an analytics comment |
| Advanced automation & integrations (Growth and above) | 🟡 | Personal API keys exist but are gated at **Premium**, not Growth (`apikeys/service/api-key-service.ts:171`); MCP exists with per-tier token quotas; Plaid bank sync exists with no tier gate found. No outbound webhooks or Zapier. The capabilities exist, the Growth gating does not |
| Basic reporting, zero setup, mobile sync | 🟢 | Fava-backed reports, hosted ledgers, mobile OAuth client |

### Plumbing and prerequisites

| Row | Status | Evidence |
| --- | --- | --- |
| Tier derived from the Stripe price ID at request time | 🟢 | `stripe/operations/get-user-tier.ts` |
| Grandfathering old prices to old limits | 🟢 | Follows from the above: old price IDs keep resolving to the old enum value |
| Sign-up question: personal, my business, or my clients' books | 🔴 | `auth/components/register-form` collects name, email and password only |
| CTA surfaces grouped by audience segment in the weekly report | 🔴 | Planned as CMS `w2/m71/t003` |
| Canadian GST/HST bookkeeping guide | 🔴 | Planned as CMS `w2/m71/t002` |
| `/for-small-business` lander | 🟡 | CMS `w2/m69` in progress; the small-business tag cohort is already on disk in `audience-content-cohorts.ts` |

## Worked check of the yearly figures

Convention from the existing Growth and Organization prices: the yearly amount is a monthly figure multiplied by twelve, with the yearly-equivalent monthly figure ending in .99.

| Plan | Yearly-equivalent monthly | × 12 | Yearly amount | Saving versus 12 monthly payments |
| --- | --- | --- | --- | --- |
| Business | $23.99 | 12 | $287.88 | $359.88 − $287.88 = $72.00 |
| Practice 50 | $159.99 | 12 | $1,919.88 | $2,399.88 − $1,919.88 = $480.00 |

Both savings equal 2.4 months of the monthly price, matching Growth ($1,199.88 − $959.88 = $240.00) and Organization ($5,999.88 − $4,799.88 = $1,200.00). These are arithmetic checks on proposed prices, not committed amounts.
