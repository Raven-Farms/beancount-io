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
 * The current parser's form: `… syntax error at position 26: found ')'
 * expected …`. Its position is a 0-based UTF-8 byte offset into the query
 * (30 for the `)` after `'日本'`), and the expected-token list is never
 * shown. The token rules match the legacy form's.
 */
const FOUND_TOKEN_PATTERN =
  /\bsyntax error at position (\d{1,6}): found '([A-Za-z0-9_.,;()*=!~+-]{1,32})' expected\b/;

const utf8 = new TextEncoder();

/**
 * The 1-based character at which `token` starts in `query`, given its 0-based
 * UTF-8 byte offset; null when the offset does not land on that token, so a
 * mismatched query never yields a wrong position (w4/971).
 */
function characterAtByteOffset(
  query: string,
  byteOffset: number,
  token: string,
): number | null {
  let bytes = 0;
  let units = 0;
  let characters = 0;
  for (const character of query) {
    if (bytes === byteOffset) {
      return query.startsWith(token, units) ? characters + 1 : null;
    }
    if (bytes > byteOffset) return null;
    bytes += utf8.encode(character).length;
    units += character.length;
    characters += 1;
  }
  return null;
}

/**
 * Resolve a query error to editor feedback. A recognized unknown-column
 * diagnostic names the offending identifier and a parser diagnostic names the
 * unexpected token and where it is; everything else falls back to
 * the shared, generic mapping — raw server messages are never shown.
 */
export function getQueryErrorFeedback(
  error: unknown,
  query?: string,
): QueryErrorFeedback {
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
      const found = FOUND_TOKEN_PATTERN.exec(gqlError.message);
      const position =
        found && query !== undefined
          ? characterAtByteOffset(query, Number(found[1]), found[2])
          : null;
      if (found && position !== null) {
        return {
          key: "bql.errors.syntaxError",
          params: { token: found[2], position: String(position) },
        };
      }
    }
  }
  return { key: getErrorMessageKey(error) };
}
