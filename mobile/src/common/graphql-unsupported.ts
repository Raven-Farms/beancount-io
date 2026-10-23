/**
 * Whether a failure is the server rejecting the document itself: a field, an
 * argument or a type it does not know. That is what a server older than the app
 * answers to a selection or an argument added later (`getLedgerErrors`' `code`
 * and `hint`, `createLedger`'s `setup` and `requestId`), with a validation
 * error before anything runs (w21/591, w21/592).
 *
 * Free of `@/` imports so the jest-lite runner can require it.
 */
const REJECTED_DOCUMENT =
  /Cannot query field|Unknown argument|Unknown type|is not defined by type/i;

export function isUnsupportedDocumentError(error: unknown): boolean {
  if (typeof error !== "object" || error === null) return false;
  const { graphQLErrors, message } = error as {
    graphQLErrors?: ReadonlyArray<{
      message?: string;
      extensions?: { code?: string };
    }>;
    message?: unknown;
  };
  const rejects = (text: unknown) =>
    typeof text === "string" && REJECTED_DOCUMENT.test(text);
  return (
    rejects(message) ||
    (Array.isArray(graphQLErrors) &&
      graphQLErrors.some(
        (err) =>
          err.extensions?.code === "GRAPHQL_VALIDATION_FAILED" ||
          rejects(err.message),
      ))
  );
}
