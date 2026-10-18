import { z } from "zod";
import { parseLedgerId } from "@/shared/str";
import { ErrorCategory } from "@/shared/errors";
import {
  pullRequestCreateInput,
  pullRequestResultSchema,
} from "@/features/gitea/pull-request/api/pull-request-routes";
import {
  resolveMcpLedger,
  ledgerSelection,
  type McpRequestContext,
} from "./mcp-context";
import { mcpOutputSchema, toolOutputSchema } from "../tools/types";
export const pullRequestToolInput = z
  .object({
    operation: z.enum(["create", "approve", "reject"]),
    ledger: ledgerSelection,
    prNumber: z.number().int().optional(),
    title: z.string().optional(),
    description: z.string().nullish(),
    baseBranch: z.string().optional(),
    clearCommitMessage: z.string().optional(),
    fastForward: z.boolean().optional(),
    changes: pullRequestCreateInput.shape.changes.optional(),
  })
  .strict();
/** One MCP tool per pull-request operation (ADR 019, 2026-10-18; w1/m38). */
const prNumber = z.number().int().describe("The pull request's number.");
export const PULL_REQUEST_OPERATION_SCHEMAS = {
  create: pullRequestCreateInput.extend({ ledger: ledgerSelection }),
  approve: z.object({ ledger: ledgerSelection, prNumber }).strict(),
  reject: z.object({ ledger: ledgerSelection, prNumber }).strict(),
} as const;
export const pullRequestToolOutput = mcpOutputSchema(
  toolOutputSchema(pullRequestResultSchema),
);
const reviewPayload = z.object({ prNumber: z.number().int() }).strict();
export async function executePullRequestTool(
  context: McpRequestContext,
  input: z.infer<typeof pullRequestToolInput>,
) {
  const { operation, ledger, ...payload } = pullRequestToolInput.parse(input);
  const { ledgerOwner: owner, ledgerName: name } = parseLedgerId(
    resolveMcpLedger(context, ledger),
  );
  const workflow = context.pullRequestWorkflow;
  const result =
    operation === "create"
      ? await workflow.createPullRequestFromPatch(
          {
            ledgerOwner: owner,
            ledgerName: name,
            ...pullRequestCreateInput.parse(payload),
          },
          context.identity,
        )
      : await workflow[
          operation === "approve" ? "approvePullRequest" : "rejectPullRequest"
        ](owner, name, reviewPayload.parse(payload).prNumber, context.identity);
  return result.success
    ? { ok: true, result }
    : {
        ok: false,
        error: result.message ?? "Pull request operation failed",
        // The repository's refusal — already merged, a conflict, a write Gitea
        // refused — is the result REST and GraphQL return as success:false.
        // Coded, so the production mask for unexpected errors keeps it.
        errorCode: ErrorCategory.OPERATION_NOT_ALLOWED,
        result,
      };
}
