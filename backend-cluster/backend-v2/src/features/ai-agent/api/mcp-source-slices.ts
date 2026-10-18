import {
  deleteSliceInput,
  deleteSlicesInput,
  updateSliceInput,
  deleteSliceResult,
  deleteSlicesResult,
  updateSliceResult,
} from "@/features/ledger/api/rest/v1/source-slice-handler";
import {
  mcpOutputSchema,
  toolOutputSchema,
  withWriteOutcome,
} from "../tools/types";
import {
  summarizeWrite,
  withPostWriteValidation,
} from "../tools/write-validation";
import {
  resolveMcpLedger,
  ledgerSelection,
  type McpRequestContext,
} from "./mcp-context";

/** One MCP tool per entry-source operation (ADR 019, 2026-10-18; w1/m38). */
export const SOURCE_SLICE_OPERATION_SCHEMAS = {
  update: updateSliceInput.extend({ ledger: ledgerSelection }),
  delete: deleteSliceInput.extend({ ledger: ledgerSelection }),
  delete_many: deleteSlicesInput.extend({ ledger: ledgerSelection }),
} as const;

/** Each tool publishes only its own result shape, not the union of all three. */
export const SOURCE_SLICE_OPERATION_OUTPUTS = {
  update: mcpOutputSchema(
    toolOutputSchema(withWriteOutcome(updateSliceResult.shape)),
  ),
  delete: mcpOutputSchema(
    toolOutputSchema(withWriteOutcome(deleteSliceResult.shape)),
  ),
  delete_many: mcpOutputSchema(
    toolOutputSchema(withWriteOutcome(deleteSlicesResult.shape)),
  ),
} as const;
/**
 * Runs one entry-source write, then reports it the way every write tool does:
 * a summary, the result, the touched entry hashes, and bean-check's verdict.
 */
function validated<T extends object>(
  context: McpRequestContext,
  ledgerId: string,
  write: () => Promise<T>,
  summarize: (written: T) => string,
  hashes: (written: T) => string[],
) {
  return withPostWriteValidation(
    context.services,
    context.identity,
    ledgerId,
    write,
  ).then(({ written, validation }) => ({
    ok: true as const,
    result: {
      summary: summarizeWrite(summarize(written), validation),
      ...written,
      wrote: [],
      entryHashes: hashes(written),
      validation,
    },
  }));
}

/** Each tool's handler, parsing the schema that tool publishes. */
export const SOURCE_SLICE_EXECUTORS = {
  update: (context: McpRequestContext, input: unknown) => {
    const { ledger, ...args } =
      SOURCE_SLICE_OPERATION_SCHEMAS.update.parse(input);
    const ledgerId = resolveMcpLedger(context, ledger);
    return validated(
      context,
      ledgerId,
      () =>
        context.services.ledgerJournal.updateSourceSlice({
          identity: context.identity,
          ledgerId,
          ...args,
        }),
      (written) =>
        `Updated entry ${written.entryHash} (new hash ${written.newEntryHash})`,
      (written) => [written.newEntryHash],
    );
  },
  delete: (context: McpRequestContext, input: unknown) => {
    const { ledger, ...args } =
      SOURCE_SLICE_OPERATION_SCHEMAS.delete.parse(input);
    const ledgerId = resolveMcpLedger(context, ledger);
    return validated(
      context,
      ledgerId,
      () =>
        context.services.ledgerJournal.deleteSourceSlice({
          identity: context.identity,
          ledgerId,
          ...args,
        }),
      (written) => `Deleted entry ${written.entryHash}`,
      (written) => [written.entryHash],
    );
  },
  delete_many: (context: McpRequestContext, input: unknown) => {
    const { ledger, entries } =
      SOURCE_SLICE_OPERATION_SCHEMAS.delete_many.parse(input);
    const ledgerId = resolveMcpLedger(context, ledger);
    return validated(
      context,
      ledgerId,
      () =>
        context.services.ledgerJournal.deleteMultiSourceSlices({
          identity: context.identity,
          ledgerId,
          entries,
        }),
      (written) =>
        `Deleted ${written.deletedCount} ${written.deletedCount === 1 ? "entry" : "entries"}`,
      () => entries.map((entry) => entry.entryHash),
    );
  },
};
