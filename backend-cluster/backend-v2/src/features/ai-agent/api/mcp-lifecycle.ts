import { z } from "zod";
import {
  ledgerCreateInput,
  ledgerUpdateInput,
  ledgerDeleteInput,
  ledgerPreviewInput,
  ledgerPreviewResultSchema,
  ledgerResultSchema,
} from "@/features/ledger/api/rest/v1/lifecycle-handler";
import {
  type McpRequestContext,
  ledgerSelection,
  resolveMcpLedger,
} from "./mcp-context";
import { mcpOutputSchema, toolOutputSchema } from "../tools/types";
/**
 * One MCP tool per lifecycle operation (ADR 019, 2026-10-18; w1/m38), each
 * taking exactly REST's input for that operation plus the ledger target.
 */
export const LIFECYCLE_OPERATION_SCHEMAS = {
  create: ledgerCreateInput,
  preview: ledgerPreviewInput,
  update: ledgerUpdateInput.extend({ ledger: ledgerSelection }),
  delete: ledgerDeleteInput.extend({ ledger: ledgerSelection }),
} as const;
export const lifecycleToolOutput = mcpOutputSchema(
  toolOutputSchema(
    z.union([ledgerResultSchema, z.object({ ledgerId: z.string() })]),
  ),
);
export const previewToolOutput = mcpOutputSchema(
  toolOutputSchema(ledgerPreviewResultSchema),
);

/** Each tool's handler, parsing the schema that tool publishes. */
export const LIFECYCLE_EXECUTORS = {
  create: async (context: McpRequestContext, input: unknown) => ({
    ok: true,
    result: await context.ledgerWorkflow.createLedger({
      identity: context.identity,
      input: LIFECYCLE_OPERATION_SCHEMAS.create.parse(input),
      platform: context.platform,
    }),
  }),
  preview: async (context: McpRequestContext, input: unknown) => ({
    ok: true,
    result: await context.ledgerWorkflow.previewLedgerSetup({
      identity: context.identity,
      setup: LIFECYCLE_OPERATION_SCHEMAS.preview.parse(input).setup,
    }),
  }),
  update: async (context: McpRequestContext, input: unknown) => {
    const { ledger, ...payload } =
      LIFECYCLE_OPERATION_SCHEMAS.update.parse(input);
    return {
      ok: true,
      result: await context.ledgerWorkflow.updateLedger({
        identity: context.identity,
        ledgerId: resolveMcpLedger(context, ledger),
        input: payload,
      }),
    };
  },
  delete: async (context: McpRequestContext, input: unknown) => {
    const { ledger } = LIFECYCLE_OPERATION_SCHEMAS.delete.parse(input);
    return {
      ok: true,
      result: await context.ledgerWorkflow.deleteLedger({
        identity: context.identity,
        ledgerId: resolveMcpLedger(context, ledger),
      }),
    };
  },
};
