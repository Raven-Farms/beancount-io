import { z } from "@/shared/zod-openapi-setup";
import { ledgerIdOf, ledgerPathSchema } from "./schemas";
import { v1Route } from "@/server/rest/v1-route";
import { json } from "@/server/rest/v1-schemas";

/**
 * The ledger's effective core options (w6/m3): the read GraphQL serves as
 * `Ledger.options`, over the same `LedgerWorkflow.getLedgerOptions` call.
 */
export const LEDGER_OPTIONS_READ = {
  summary: "Get the ledger's core options",
  description:
    "The effective Beancount options: title, the five account-root names, the current conversions and earnings accounts, comma rendering, and the operating currencies. Values are what the ledger resolves, defaults included, so a client need not parse option lines. `operatingCurrency` is what the ledger reports in; the currencies its postings use are a separate vocabulary read.",
} as const;

const ledgerOptionsSchema = z.object({
  title: z.string(),
  nameAssets: z.string().openapi({ example: "Assets" }),
  nameEquity: z.string().openapi({ example: "Equity" }),
  nameExpenses: z.string().openapi({ example: "Expenses" }),
  nameIncome: z.string().openapi({ example: "Income" }),
  nameLiabilities: z.string().openapi({ example: "Liabilities" }),
  accountCurrentConversions: z
    .string()
    .openapi({ example: "Conversions:Current" }),
  accountCurrentEarnings: z.string().openapi({ example: "Earnings:Current" }),
  renderCommas: z.boolean(),
  operatingCurrency: z.array(z.string()).openapi({ example: ["USD"] }),
});

export const LEDGER_OPTIONS_ROUTE = v1Route({
  method: "get",
  path: "/api-gateway/v1/ledgers/{owner}/{name}/options",
  summary: LEDGER_OPTIONS_READ.summary,
  description: LEDGER_OPTIONS_READ.description,
  params: ledgerPathSchema,
  responses: { 200: json(LEDGER_OPTIONS_READ.summary, ledgerOptionsSchema) },
  handler: async ({ layers }, { identity, params }) =>
    layers.workflows.ledger.getLedgerOptions({
      ledgerId: ledgerIdOf(params),
      identity,
    }),
});
