import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { getErrorMessageKey } from "@/common/lib/errors/error-message";

/**
 * A localized query-error message: an i18n key plus its interpolation values.
 */
export interface QueryErrorFeedback {
  key: string;
  params?: Record<string, string>;
}

/**
 * The engine's unknown-column diagnostic, as the ledger service forwards it
 * inside a BAD_USER_INPUT error: `… column 'nonexistent_column' not found`.
 * Only a plain BQL identifier is captured, so arbitrary server text can never
 * reach the page through the interpolated value.
 */
const UNKNOWN_COLUMN_PATTERN =
  /\bcolumn '([A-Za-z_][A-Za-z0-9_.]{0,63})' not found\b/;

/**
 * The engine's parser diagnostic: `… syntax error at position 16: unexpected
 * token 'FROM'`. The position is a 0-based character offset. Only a short,
 * quote- and angle-bracket-free token is accepted, so the interpolated value
 * cannot carry arbitrary server text into the page.
 */
const SYNTAX_ERROR_PATTERN =
  /\bsyntax error at position (\d{1,6}): unexpected token '([A-Za-z0-9_.,;()*=!~+-]{1,32})'(?!\S)/;

/**
 * Resolve a query error to editor feedback. A recognized unknown-column
 * diagnostic names the offending identifier and a parser diagnostic names the
 * unexpected token and where it is; everything else falls back to
 * the shared, generic mapping — raw server messages are never shown.
 */
export function getQueryErrorFeedback(error: unknown): QueryErrorFeedback {
  if (CombinedGraphQLErrors.is(error)) {
    for (const gqlError of error.errors) {
      if (gqlError.extensions?.code !== "BAD_USER_INPUT") continue;
      const match = UNKNOWN_COLUMN_PATTERN.exec(gqlError.message);
      if (match) {
        return {
          key: "bql.errors.unknownColumn",
          params: { column: match[1] },
        };
      }
      const syntax = SYNTAX_ERROR_PATTERN.exec(gqlError.message);
      if (syntax) {
        return {
          key: "bql.errors.syntaxError",
          // Readers count characters from 1; the engine counts from 0.
          params: { token: syntax[2], position: String(Number(syntax[1]) + 1) },
        };
      }
    }
  }
  return { key: getErrorMessageKey(error) };
}
