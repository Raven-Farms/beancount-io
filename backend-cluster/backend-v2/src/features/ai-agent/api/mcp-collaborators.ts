import {
  collaboratorUpdateInput,
  collaboratorDeleteInput,
  collaboratorLeaveInput,
  collaboratorResultSchema,
} from "@/features/ledger/api/rest/v1/collaborators-handler";
import {
  resolveMcpLedger,
  ledgerSelection,
  type McpRequestContext,
} from "./mcp-context";
import { mcpOutputSchema, toolOutputSchema } from "../tools/types";

/** One MCP tool per collaborator operation (ADR 019, 2026-10-18; w1/m38). */
export const COLLABORATOR_OPERATION_SCHEMAS = {
  update: collaboratorUpdateInput.extend({
    ledger: ledgerSelection,
    permission: collaboratorUpdateInput.shape.permission.describe(
      "read, write, or admin; omitted or null uses the repository default.",
    ),
  }),
  delete: collaboratorDeleteInput.extend({ ledger: ledgerSelection }),
  leave: collaboratorLeaveInput.extend({ ledger: ledgerSelection }),
} as const;

export const collaboratorToolOutput = mcpOutputSchema(
  toolOutputSchema(collaboratorResultSchema),
);

function target(context: McpRequestContext, ledger: string | undefined) {
  return {
    identity: context.identity,
    ledgerId: resolveMcpLedger(context, ledger),
  };
}

/** Each tool's handler, parsing the schema that tool publishes. */
export const COLLABORATOR_EXECUTORS = {
  update: async (context: McpRequestContext, input: unknown) => {
    const { ledger, collaborator, permission } =
      COLLABORATOR_OPERATION_SCHEMAS.update.parse(input);
    return {
      ok: true,
      result: await context.collaboratorsWorkflow.addOrUpdateCollaborator({
        ...target(context, ledger),
        collaborator,
        permission: permission ?? undefined,
      }),
    };
  },
  delete: async (context: McpRequestContext, input: unknown) => {
    const { ledger, ...payload } =
      COLLABORATOR_OPERATION_SCHEMAS.delete.parse(input);
    return {
      ok: true,
      result: await context.collaboratorsWorkflow.deleteCollaborator({
        ...target(context, ledger),
        ...payload,
      }),
    };
  },
  leave: async (context: McpRequestContext, input: unknown) => {
    const { ledger } = COLLABORATOR_OPERATION_SCHEMAS.leave.parse(input);
    return {
      ok: true,
      result: await context.collaboratorsWorkflow.leaveLedger(
        target(context, ledger),
      ),
    };
  },
};
