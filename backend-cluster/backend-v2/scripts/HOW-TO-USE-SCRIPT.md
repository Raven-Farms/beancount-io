# Script Usage Guide

Standalone maintenance and codegen scripts live in this directory. Run them with
`ts-node`/`tsx` and `tsconfig-paths` so the `@/` path aliases resolve, e.g.:

```bash
npx ts-node -r tsconfig-paths/register --transpile-only ./scripts/<script>.ts
```

## Available Scripts

- `collect-directive-counts.ts` — collect Beancount directive counts across ledgers.
- `decrypt-plaid-token.ts` — decrypt a stored Plaid access token for debugging.
- `generate-agent-tool-types.ts` — generate TypeScript types for agent tools.
- `generate-openapi-spec.ts` — export the backend-v2 REST admin OpenAPI spec.
- `nanoid-base58.ts` — generate base58 nanoid values.

> **Note:** The MongoDB backup/upgrade scripts documented here previously have been
> removed. The backend now runs on PostgreSQL (Drizzle ORM) + Redis.

## Retire historical test billing caches

Application billing supports only `beancount-web-prod`. The backend derives the
highest recognized **active live** tier from the subscription's own customer and
price; unknown prices do not imply Premium. The period cache is not an entitlement.
Historical test bindings are retained for audit, with their obsolete period cache
cleared by this tool. No account, ledger, Stripe object, charge, discount or coupon
is changed. Email is never used to guess ownership.

Deploy the backend and dashboard changes together before applying repairs. Supply
`POSTGRES_BACKEND_URI` and `STRIPE_PRIVATE_KEY` through the deployment's secret
manager, never command arguments or checked-in files. Run from this package in an
authorized service environment. An image without `.git` must receive the verified
deployed commit as `--revision <full-40-character-sha>` on preview and apply; apply
rejects a plan from a different source revision. Only a live Stripe key is accepted; testing uses
synthetic provider fixtures and an isolated PostgreSQL container.

Preview is the default and makes **zero database or Stripe writes**. It writes a
private plan using exclusive creation and mode `0600`. All plan and journal paths
must be absolute and outside the git checkout; create their parent directory first.
For example, with a private `/tmp/billing-cutover` directory:

```bash
yarn ts-node -r tsconfig-paths/register --transpile-only scripts/reconcile-billing.ts \
  --preview --limit 100 --output /tmp/billing-cutover/preview-001.json
```

The report contains a fixed `createdBefore`/`through` cohort boundary, `after`/`next`
keyset checkpoint, remaining count, source revision, per-user classifications and a
change fingerprint. Stdout contains only aggregate counts and the fingerprint.
Review the private plan and deployed revision. No-history users are unchanged;
test-only users gain no paid access. Missing/deleted customers, unknown active
prices, ambiguous bindings and failed provider lookups remain unresolved and are
never treated as an empty paid history. Classification counts sum to scanned users.

Apply requires that exact reviewed fingerprint, at most 500 users and a new journal:

```bash
yarn ts-node -r tsconfig-paths/register --transpile-only scripts/reconcile-billing.ts \
  --apply /tmp/billing-cutover/preview-001.json --fingerprint <reviewed-sha256> \
  --journal /tmp/billing-cutover/apply-001.jsonl
```

Each user is re-read from live Stripe, then all their binding versions are compared
inside a PostgreSQL transaction. Any changed preview/provider state stops apply;
concurrent cache updates cannot be overwritten. A rollback snapshot is flushed
before committing, followed by a committed record and read-back. A provider outage
never clears a cache. Completed transactions remain committed if a later user
fails; generate a new preview for the **same batch boundary** and retry. Already
repaired users are no-ops. Keep every journal.

Continue the next batch with `--after <next>` plus the **original**
`--through <through>` and `--created-before <createdBefore>` from the private plan.
Do not advance the checkpoint past an unresolved case without recording it for
separate investigation. Sum scanned/classification counts across batches until
remaining is zero. Re-preview the cohort for idempotence; verify representative
profile/CLI tier, settings product/current plan, and effective ledger/collaborator
limits without making a purchase. Record only aggregate results in `.pm/`.

Rollback restores only cache values whose complete binding versions still match
the committed snapshot; it refuses to overwrite newer billing/webhook activity:

```bash
yarn ts-node -r tsconfig-paths/register --transpile-only scripts/reconcile-billing.ts \
  --rollback /tmp/billing-cutover/apply-001.jsonl \
  --journal /tmp/billing-cutover/rollback-001.jsonl
```

If a process stops between database commit and the committed journal record, do
not infer success or blindly restore the before snapshot. Retain the journal,
read back the affected batch, and generate a fresh preview. Unresolved cases and
production access failures leave the rollout ticket open.
