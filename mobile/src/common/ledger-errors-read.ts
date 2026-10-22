import type { ApolloClient } from "@apollo/client";
import {
  GetLedgerErrorsBasicDocument,
  GetLedgerErrorsDocument,
  type GetLedgerErrorsBasicQuery,
  type GetLedgerErrorsQuery,
} from "../generated-graphql/graphql";
import { isUnsupportedDocumentError } from "./graphql-unsupported";
import type { LedgerError } from "./new-ledger-error";

/** See `isUnsupportedDocumentError`: the `code` and `hint` of w21/311 are what an older server rejects (w21/591). */
export const isUnknownFieldError = isUnsupportedDocumentError;

/** The basic read's rows as `LedgerError`s, which carry no code or hint. */
export function basicLedgerErrors(
  data: GetLedgerErrorsBasicQuery | undefined,
): LedgerError[] | undefined {
  return data?.getLedgerErrors.map((error) => ({
    ...error,
    hint: null,
  }));
}

/**
 * The ledger's errors for a one-off read (the editor's check after a save): the
 * full document, then the basic one when the server rejects its fields.
 */
export async function queryLedgerErrors(
  client: ApolloClient<object>,
  ledgerId: string,
): Promise<LedgerError[] | undefined> {
  try {
    const { data } = await client.query<GetLedgerErrorsQuery>({
      query: GetLedgerErrorsDocument,
      variables: { ledgerId },
      fetchPolicy: "cache-first",
    });
    return data?.getLedgerErrors;
  } catch (error) {
    if (!isUnknownFieldError(error)) throw error;
    const { data } = await client.query<GetLedgerErrorsBasicQuery>({
      query: GetLedgerErrorsBasicDocument,
      variables: { ledgerId },
      fetchPolicy: "cache-first",
    });
    return basicLedgerErrors(data);
  }
}
