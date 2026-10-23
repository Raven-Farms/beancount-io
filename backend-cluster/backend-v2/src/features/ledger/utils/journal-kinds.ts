import {
  CustomSubtype,
  DirectiveType,
  DocumentSubtype,
  TransactionSubtype,
} from "@/foundation/fava";
import { BadUserInputError } from "@/shared/errors";

/**
 * The directive kinds and subtypes a journal read can select, and the one
 * rule every surface applies to them (w23/006).
 *
 * The ledger service filters by exact match, so before this an unknown or
 * lowercase kind — `"transaction"`, the spelling `addLedgerEntries` takes —
 * came back as an empty success, and an agent reading back what it wrote
 * concluded the entries were missing. Case is ignored; anything else is
 * refused naming the valid values. An empty list keeps its meaning.
 */
export const JOURNAL_KINDS = {
  directiveTypes: Object.values(DirectiveType),
  transactionSubtypes: Object.values(TransactionSubtype),
  documentSubtypes: Object.values(DocumentSubtype),
  customSubtypes: Object.values(CustomSubtype),
} as const;

type KindField = keyof typeof JOURNAL_KINDS;
type Kind<Field extends KindField> = (typeof JOURNAL_KINDS)[Field][number];

function normalize<Field extends KindField>(
  field: Field,
  values: readonly string[] | null | undefined,
): Kind<Field>[] | undefined {
  if (values === null || values === undefined) return undefined;
  const allowed: readonly Kind<Field>[] = JOURNAL_KINDS[field];
  return values.map((value) => {
    const kind = allowed.find(
      (candidate) => candidate.toLowerCase() === value.toLowerCase(),
    );
    if (kind === undefined) {
      throw new BadUserInputError(
        `Unknown ${field} value "${value}"`,
        field,
        `Use any of ${allowed.join(", ")}; case does not matter.`,
      );
    }
    return kind;
  });
}

export interface JournalKindSelection {
  directiveTypes?: readonly string[] | null;
  transactionSubtypes?: readonly string[] | null;
  documentSubtypes?: readonly string[] | null;
  customSubtypes?: readonly string[] | null;
}

/** The selection in the ledger service's spelling, or a BAD_USER_INPUT. */
export function normalizeJournalKinds(query: JournalKindSelection | undefined) {
  return {
    directive_types: normalize("directiveTypes", query?.directiveTypes),
    transaction_subtypes: normalize(
      "transactionSubtypes",
      query?.transactionSubtypes,
    ),
    document_subtypes: normalize("documentSubtypes", query?.documentSubtypes),
    custom_subtypes: normalize("customSubtypes", query?.customSubtypes),
  };
}
