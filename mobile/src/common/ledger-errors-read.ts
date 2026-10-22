import type { ApolloClient } from "@apollo/client";
import {
  GetLedgerErrorsBasicDocument,
  GetLedgerErrorsDocument,
  type GetLedgerErrorsBasicQuery,
  type GetLedgerErrorsQuery,
} from "../generated-graphql/graphql";
import type { LedgerError } from "./new-ledger-error";

/**
 * Whether a failure is the server rejecting a field of the document, which is
 * what a server older than the app answers to a selection it does not know.
 * `getLedgerErrors` gained `code` and `hint` on 2026-10-21 (w21/311), and an
 * older server (a self-hosted one the app promises to work with) rejected the
 * whole query: Notifications failed, the bell read 0 and the editor's error
 * checks went silent, so a ledger that was broken looked clean (w21/591).
 */
export function isUnknownFieldError(error: unknown): boolean {
  if (typeof error !== "object" || error === null) return false;
  const { graphQLErrors, message } = error as {
    graphQLErrors?: ReadonlyArray<{
      message?: string;
      extensions?: { code?: string };
    }>;
    message?: unknown;
  };
  const validation = (text: unknown) =>
    typeof text === "string" && /Cannot query field/i.test(text);
  return (
    validation(message) ||
    (Array.isArray(graphQLErrors) &&
      graphQLErrors.some(
        (err) =>
          err.extensions?.code === "GRAPHQL_VALIDATION_FAILED" ||
          validation(err.message),
      ))
  );
}

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
