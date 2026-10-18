import { z } from "zod";
import { BadUserInputError } from "@/shared/errors";
import { logger } from "@/shared/logger";
import type { ToolContext } from "./types";
import {
  toolOutputSchema,
  writeValidationSchema,
  wroteFileSchema,
} from "./types";
import { runToolSafely } from "../utils/run-tool";
import {
  readBeanCheckErrors,
  summarizeWrite,
  toWriteValidation,
  withPostWriteValidation,
} from "./write-validation";

const toolLogger = logger.child({ module: "tool:bank" });

/**
 * The bank verbs, split along the line their op classes already draw
 * (ADR 0008 D3).
 *
 * This began as one eight-verb tool and the op-class registry refused it: the
 * single tool id would have been classified `write` by `syncPlaidTransactions`
 * and `admin` by `refreshPlaidItemStatus`. That is D3 enforcing itself —
 * grouping is legitimate when members share a shape **and an authorization
 * class**, and that grouping had only the first.
 *
 * The split is not a concession. A credential that may import transactions
 * should not thereby be able to sever the bank connection, and one tool would
 * have made those the same permission.
 *
 * Linking a *new* bank appears in neither: the operation is a hosted browser
 * widget, so there is no API to expose (ADR 0008 D4).
 */

const dryRunField = z
  .boolean()
  .optional()
  .describe(
    "Validate and report what would change, without changing anything.",
  );

// --- import workflow (write class) ------------------------------------------

/**
 * The bank-import payload is service-defined per operation, so the schema
 * stays open — but `submit` (the one operation that writes ledger entries)
 * carries the same write outcome as every other write tool (w2/m26), and
 * those fields are published here so `tools/list` advertises them.
 */
export const bankImportOutputSchema = toolOutputSchema(
  z
    .object({
      summary: z.string().optional(),
      wrote: z.array(wroteFileSchema).optional(),
      entryHashes: z.array(z.string()).optional(),
      validation: writeValidationSchema.optional(),
    })
    .catchall(z.unknown()),
);

// --- connection control plane (admin class) ---------------------------------

export const bankConnectionOutputSchema = toolOutputSchema(z.unknown());

// --- one MCP tool per operation (ADR 019, 2026-10-18; w1/m38) ---------------
//
// MCP exposes each operation above as its own tool, with only that operation's
// fields and those fields required where the operation needs them. The two
// executors stay the shared implementation; each tool fixes its `operation`.

const itemIdField = z.string().describe("The linked bank's id (item_id).");
const accountIdField = z
  .string()
  .describe("The linked bank account's id (account_id).");

export const BANK_OPERATION_SCHEMAS = {
  sync: z.object({ item_id: itemIdField, dry_run: dryRunField }),
  submit: z.object({
    transactions: z
      .array(
        z.object({
          transaction_id: z.string(),
          target_account: z
            .string()
            .describe("The ledger account to book this against."),
          source_account: z.string().optional(),
        }),
      )
      .min(1)
      .describe("The staged transactions to write."),
    filename: z
      .string()
      .optional()
      .describe("Which ledger file to append to. Must exist."),
    dry_run: dryRunField,
  }),
  discard: z.object({
    transaction_ids: z
      .array(z.string())
      .min(1)
      .describe("The staged transactions to remove."),
    dry_run: dryRunField,
  }),
  reconcile: z.object({ item_id: itemIdField, dry_run: dryRunField }),
  map_account: z.object({
    account_id: accountIdField,
    ledger_account: z.string().describe("The ledger account to map it to."),
  }),
  set_currency: z.object({
    account_id: accountIdField,
    currency: z.string().describe("The account's currency, e.g. USD."),
  }),
  refresh: z.object({ item_id: itemIdField }),
  unlink: z.object({ item_id: itemIdField, dry_run: dryRunField }),
} as const;

export const BANK_OPERATION_DESCRIPTIONS = {
  sync: "Pull new transactions from a linked bank into staging; nothing is written to the ledger. dry_run reports what would be pulled.",
  submit:
    "Write staged bank transactions into the ledger as directives, each booked against the given target account. dry_run returns the result and projected validation without committing.",
  discard:
    "Remove staged bank transactions so they are never imported. dry_run reports what would be removed.",
  reconcile:
    "Re-read which accounts a linked bank shares; accounts the bank no longer shares can be deleted along with their staged transactions. dry_run reports the changes without applying them.",
  map_account:
    "Point a linked bank account at a ledger account; replaces any existing mapping.",
  set_currency:
    "Set a linked bank account's currency; replaces the current value.",
  refresh: "Re-read a linked bank connection's health status from the bank.",
  unlink:
    "Sever a linked bank connection. Linking a new bank happens in a browser through the bank's own widget, not here. dry_run reports what would be removed.",
} as const;

type Schemas = typeof BANK_OPERATION_SCHEMAS;
type Fields<K extends keyof Schemas> = Partial<z.infer<Schemas[K]>>;
type ImportInput = Fields<"sync"> &
  Fields<"submit"> &
  Fields<"discard"> & { operation: "sync" | "submit" | "discard" };
type ConnectionInput = Fields<"reconcile"> &
  Fields<"map_account"> &
  Fields<"set_currency"> &
  Fields<"refresh"> &
  Fields<"unlink"> & {
    operation:
      | "reconcile"
      | "map_account"
      | "set_currency"
      | "refresh"
      | "unlink";
  };
type BankCtx = Pick<ToolContext, "services" | "identity" | "ledgerId">;

/**
 * A required argument, refused by name.
 *
 * Without this a missing `item_id` reaches the service as `undefined` and comes
 * back as "Item not found" — which sends a model looking for the wrong problem.
 * A plain `Error` here surfaced as INTERNAL_SERVER_ERROR with "retry once", so
 * it is a bad-input error: the caller can fix it and a retry cannot.
 */
function required<T>(value: T | undefined, key: string, operation: string): T {
  if (value === undefined || value === null) {
    throw new BadUserInputError(
      `\`${key}\` is required for operation "${operation}"`,
      key,
      `Pass \`${key}\` with operation "${operation}"; \`tools/list\` publishes each tool's input schema.`,
    );
  }
  return value;
}

export async function executeBankImport(ctx: BankCtx, input: ImportInput) {
  const { services, identity, ledgerId } = ctx;
  const dryRun = input.dry_run ?? false;
  toolLogger.debug("Bank import", { operation: input.operation, dryRun });

  return runToolSafely({
    logger: toolLogger,
    message: "Bank import failed",
    context: { operation: input.operation },
    execute: async () => {
      switch (input.operation) {
        case "sync":
          return services.plaidSync.syncItemTransactions(
            identity,
            required(input.item_id, "item_id", "sync"),
            "manual",
            ledgerId,
            dryRun,
          );
        case "submit": {
          const [owner, name] = ledgerId.split("/");
          const requested = required(
            input.transactions,
            "transactions",
            "submit",
          );
          const submit = () =>
            services.plaidSync.submitTransactionsToLedger(
              identity,
              owner,
              name,
              requested.map((t) => ({
                transactionId: t.transaction_id,
                targetAccount: t.target_account,
                sourceAccount: t.source_account,
              })),
              input.filename,
              dryRun,
            );
          if (dryRun) {
            const errorsBefore = await readBeanCheckErrors(
              services,
              identity,
              ledgerId,
            );
            const submitted = await submit();
            return {
              ...submitted,
              summary: `Dry run: would submit ${requested.length} bank transaction(s) — not committed.`,
              wrote: [],
              entryHashes: [],
              validation: toWriteValidation(errorsBefore, errorsBefore),
            };
          }
          const { written: submitted, validation } =
            await withPostWriteValidation(services, identity, ledgerId, submit);
          return {
            ...submitted,
            summary: summarizeWrite(
              `Submitted ${requested.length} bank transaction(s)${input.filename ? ` to ${input.filename}` : ""}`,
              validation,
            ),
            wrote: input.filename ? [{ path: input.filename }] : [],
            entryHashes: [],
            validation,
          };
        }
        case "discard":
          return services.plaidSync.deleteTransactions(
            identity,
            ledgerId,
            required(input.transaction_ids, "transaction_ids", "discard"),
            dryRun,
          );
      }
    },
  });
}

export async function executeBankConnection(
  ctx: BankCtx,
  input: ConnectionInput,
) {
  const { services, identity, ledgerId } = ctx;
  const dryRun = input.dry_run ?? false;
  toolLogger.debug("Bank connection", { operation: input.operation, dryRun });

  return runToolSafely({
    logger: toolLogger,
    message: "Bank connection operation failed",
    context: { operation: input.operation },
    execute: async () => {
      if (
        dryRun &&
        input.operation !== "reconcile" &&
        input.operation !== "unlink"
      ) {
        // The caller's to fix, as REST's 400 for the same request says — a
        // plain Error here read as a server fault to retry (w5/034).
        throw new BadUserInputError(
          `dry_run is not supported for ${input.operation}`,
          "dry_run",
          "Only `reconcile` and `unlink` can be previewed. Omit `dry_run` to perform this operation.",
        );
      }
      switch (input.operation) {
        case "reconcile":
          return services.plaidItem.reconcileItemAccounts(
            identity,
            required(input.item_id, "item_id", "reconcile"),
            ledgerId,
            dryRun,
          );
        case "unlink":
          return services.plaidItem.unlinkItem(
            identity,
            required(input.item_id, "item_id", "unlink"),
            ledgerId,
            dryRun,
          );
        case "refresh":
          return services.plaidItem.refreshItemStatus(
            identity,
            required(input.item_id, "item_id", "refresh"),
            ledgerId,
          );
        case "map_account":
          return services.plaidItem.updateAccountMapping(
            identity,
            required(input.account_id, "account_id", "map_account"),
            required(input.ledger_account, "ledger_account", "map_account"),
            ledgerId,
          );
        case "set_currency":
          return services.plaidItem.updateAccountCurrency(
            identity,
            required(input.account_id, "account_id", "set_currency"),
            required(input.currency, "currency", "set_currency"),
            ledgerId,
          );
      }
    },
  });
}
