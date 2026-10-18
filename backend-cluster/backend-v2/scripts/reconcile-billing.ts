/** Read-only by default. Private plans/rollback journals must live outside the checkout. */
import "dotenv/config";
import { createRepairStore } from "./billing-repair-store";
import { Pool } from "pg";
import {
  closeSync,
  fsyncSync,
  openSync,
  readFileSync,
  realpathSync,
  writeFileSync,
} from "node:fs";
import { basename, dirname, isAbsolute, relative, resolve } from "node:path";
import { execFileSync } from "node:child_process";
import Stripe from "stripe";
import { BILLING_CLIENT_ID } from "../src/features/stripe/service/stripe";
import {
  applyUserRepair,
  fingerprint,
  planUserRepair,
  rollbackRepair,
  type BindingSnapshot,
  type UserRepair,
} from "./reconcile-billing-core";

interface Plan {
  format: 1;
  revision: string;
  after: string;
  through: string;
  next: string;
  remaining: number;
  createdBefore: string;
  repairs: UserRepair[];
  fingerprint: string;
}
const args = process.argv.slice(2);
function option(name: string) {
  const index = args.indexOf(name);
  return index < 0 ? undefined : args[index + 1];
}
function gitValue(args: string[]): string | undefined {
  try {
    return execFileSync("git", args, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return undefined;
  }
}
function sourceRevision(): string {
  const checkedOut = gitValue(["rev-parse", "HEAD"]);
  const declared = option("--revision");
  if (checkedOut && declared && checkedOut !== declared)
    throw new Error("Source revision mismatch");
  const revision = checkedOut ?? declared;
  if (!revision || !/^[a-f0-9]{40}$/.test(revision))
    throw new Error("A verified --revision is required outside a git checkout");
  return revision;
}
function privatePath(path: string) {
  if (!isAbsolute(path))
    throw new Error(
      "Private report path must be absolute and outside the checkout",
    );
  const root =
    gitValue(["rev-parse", "--show-toplevel"]) ?? resolve(__dirname, "..");
  const parent = realpathSync(dirname(path));
  const candidate = resolve(parent, basename(path));
  const rel = relative(root, candidate);
  if (!rel.startsWith("../"))
    throw new Error("Private reports must be outside the checkout");
  return candidate;
}
function createJournal(path: string) {
  const fd = openSync(privatePath(path), "wx", 0o600);
  return {
    write(value: unknown) {
      writeFileSync(fd, JSON.stringify(value) + "\n");
      fsyncSync(fd);
    },
    close() {
      closeSync(fd);
    },
  };
}

async function main() {
  const known = new Set([
    "--preview",
    "--output",
    "--limit",
    "--after",
    "--through",
    "--created-before",
    "--apply",
    "--fingerprint",
    "--journal",
    "--rollback",
    "--revision",
  ]);
  for (let i = 0; i < args.length; i++) {
    if (!known.has(args[i])) throw new Error("Unknown option");
    if (args[i] !== "--preview") i++;
  }
  if (
    ["--preview", "--apply", "--rollback"].filter((flag) => args.includes(flag))
      .length > 1
  )
    throw new Error("Choose only one operation");
  if (!process.env.POSTGRES_BACKEND_URI)
    throw new Error("POSTGRES_BACKEND_URI is required");
  const pool = new Pool({
    connectionString: process.env.POSTGRES_BACKEND_URI,
    max: 2,
  });
  const store = createRepairStore(pool);
  const read = store.read;
  try {
    if (option("--rollback")) {
      if (!option("--journal"))
        throw new Error("Rollback requires a new --journal path");
      const records = readFileSync(privatePath(option("--rollback")!), "utf8")
        .trim()
        .split("\n")
        .map((line) => JSON.parse(line));
      const journal = createJournal(option("--journal")!);
      try {
        // Only completed transactions are eligible. Uncertain commits require a fresh preview.
        const committed = records.filter(
          (record) => record.kind === "committed",
        );
        for (const record of committed.reverse()) {
          const original = records.find(
            (row) =>
              row.kind === "before" && row.repair.userId === record.userId,
          )?.repair as UserRepair;
          if (!original) throw new Error("Missing rollback snapshot");
          const undo = rollbackRepair(original, record.after);
          journal.write({ kind: "before", repair: undo });
          const after = await store.compareAndSet(undo);
          journal.write({ kind: "committed", userId: undo.userId, after });
        }
        console.log(JSON.stringify({ restored: committed.length }));
      } finally {
        journal.close();
      }
      return;
    }
    if (!process.env.STRIPE_PRIVATE_KEY?.startsWith("sk_live_"))
      throw new Error(
        "A live STRIPE_PRIVATE_KEY is required (never pass it as a CLI argument)",
      );
    const stripe = new Stripe(process.env.STRIPE_PRIVATE_KEY, {
      apiVersion: "2025-12-15.clover",
    });
    const load = async (binding: BindingSnapshot) => {
      const customer = await stripe.customers.retrieve(
        binding.stripeCustomerId,
      );
      if (
        customer.deleted ||
        !customer.livemode ||
        (customer.metadata.userId &&
          customer.metadata.userId !== binding.userId) ||
        (customer.metadata.clientId &&
          customer.metadata.clientId !== BILLING_CLIENT_ID)
      )
        throw new Error("Missing or mismatched live customer");
      const subscriptions = await stripe.subscriptions
        .list({ customer: binding.stripeCustomerId, status: "all", limit: 100 })
        .autoPagingToArray({ limit: 10000 });
      return subscriptions.map((sub) => ({
        ...sub,
        clientId: BILLING_CLIENT_ID,
      }));
    };
    if (option("--apply")) {
      const plan: Plan = JSON.parse(
        readFileSync(privatePath(option("--apply")!), "utf8"),
      );
      const { fingerprint: expected, ...body } = plan;
      if (plan.revision !== sourceRevision())
        throw new Error("Plan revision does not match the running source");
      if (
        plan.format !== 1 ||
        plan.repairs.length > 500 ||
        expected !== fingerprint(body) ||
        expected !== option("--fingerprint") ||
        !option("--journal")
      )
        throw new Error(
          "Apply requires a reviewed bounded plan, matching --fingerprint and new --journal",
        );
      const journal = createJournal(option("--journal")!);
      let applied = 0,
        unchanged = 0,
        unresolved = 0;
      try {
        for (const repair of plan.repairs) {
          if (repair.classification === "unresolved") {
            unresolved++;
            continue;
          }
          const after = await applyUserRepair(
            repair,
            store,
            load,
            async (snapshot) => {
              journal.write({ kind: "before", repair: snapshot });
            },
          );
          if (repair.changes.length) {
            journal.write({ kind: "committed", userId: repair.userId, after });
            applied++;
          } else unchanged++;
          if (
            repair.changes.some(
              (change) =>
                after.find((row) => row.id === change.id)?.period !==
                change.period,
            )
          )
            throw new Error("Billing read-back mismatch");
        }
        console.log(
          JSON.stringify({
            scanned: plan.repairs.length,
            applied,
            unchanged,
            unresolved,
            remaining: plan.remaining,
          }),
        );
      } finally {
        journal.close();
      }
      return;
    }
    const limit = Number(option("--limit") ?? 100);
    if (
      !Number.isInteger(limit) ||
      limit < 1 ||
      limit > 500 ||
      !option("--output")
    )
      throw new Error("Preview requires --output and --limit 1..500");
    const after = option("--after") ?? "";
    const createdBefore =
      option("--created-before") ?? new Date().toISOString();
    if (!Number.isFinite(Date.parse(createdBefore)))
      throw new Error("Invalid cohort cutoff");
    if (after && (!option("--through") || !option("--created-before")))
      throw new Error(
        "Resuming requires the original --through and --created-before checkpoint",
      );
    const through =
      option("--through") ??
      (
        await pool.query(
          "SELECT max(id) AS id FROM users WHERE create_at <= $1",
          [createdBefore],
        )
      ).rows[0].id ??
      "";
    const cohort = await pool.query(
      "SELECT id FROM users WHERE id > $1 AND id <= $2 AND create_at <= $3 ORDER BY id LIMIT $4",
      [after, through, createdBefore, limit],
    );
    const repairs: UserRepair[] = [];
    for (const { id } of cohort.rows) {
      const rows = await read(id);
      try {
        repairs.push(await planUserRepair(id, rows, load));
      } catch {
        repairs.push({
          userId: id,
          before: rows,
          classification: "unresolved",
          changes: [],
          evidence: "provider-or-ownership-failure",
        });
      }
    }
    const next = cohort.rows.at(-1)?.id ?? after;
    const remaining = Number(
      (
        await pool.query(
          "SELECT count(*) AS count FROM users WHERE id > $1 AND id <= $2 AND create_at <= $3",
          [next, through, createdBefore],
        )
      ).rows[0].count,
    );
    const body = {
      format: 1 as const,
      revision: sourceRevision(),
      after,
      through,
      next,
      remaining,
      createdBefore,
      repairs,
    };
    const plan = { ...body, fingerprint: fingerprint(body) };
    const journal = createJournal(option("--output")!);
    try {
      journal.write(plan);
    } finally {
      journal.close();
    }
    const classifications: Record<string, number> = {};
    for (const repair of repairs)
      classifications[repair.classification] =
        (classifications[repair.classification] ?? 0) + 1;
    // Cursors and identities are in the private plan, never stdout.
    console.log(
      JSON.stringify({
        scanned: repairs.length,
        repairable: repairs.filter((r) => r.changes.length).length,
        classifications,
        remaining,
        fingerprint: plan.fingerprint,
      }),
    );
  } finally {
    await pool.end();
  }
}
main().catch(() => {
  console.error(
    "Billing reconciliation stopped. Check credentials, reviewed fingerprint and private journal; no provider errors are treated as an empty subscription history.",
  );
  process.exitCode = 1;
});
