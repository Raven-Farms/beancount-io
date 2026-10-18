import { useCallback, useEffect, useRef } from "react";
import {
  CombinedGraphQLErrors,
  ServerError,
  ServerParseError,
} from "@apollo/client/errors";
import { useTranslations } from "@/common/hooks/use-translations";

/**
 * Maps backend error categories (surfaced as `extensions.code` on GraphQL
 * errors — see backend-cluster/backend-v2/src/shared/errors/) to localized
 * message keys. Raw server `error.message` strings are never shown to users;
 * they are internals meant for logs.
 */
const ERROR_CODE_TO_KEY: Record<string, string> = {
  UNAUTHENTICATED: "common.errors.unauthenticated",
  FORBIDDEN: "common.errors.forbidden",
  NOT_FOUND: "common.errors.notFound",
  BAD_USER_INPUT: "common.errors.badUserInput",
  VALIDATION_FAILED: "common.errors.validationFailed",
  CONFLICT: "common.errors.conflict",
  RATE_LIMITED: "common.errors.rateLimited",
  INTERNAL_SERVER_ERROR: "common.errors.internal",
  SERVICE_UNAVAILABLE: "common.errors.serviceUnavailable",
  RESOURCE_LIMIT_REACHED: "common.errors.resourceLimitReached",
  OPERATION_NOT_ALLOWED: "common.errors.operationNotAllowed",
  PREMIUM_REQUIRED: "common.errors.premiumRequired",
  UNBALANCED: "common.errors.unbalanced",
};

const GENERIC_ERROR_KEY = "common.errors.generic";

/**
 * Resolve any thrown value (ApolloError, fetch failure, plain Error, …) to
 * the i18n key of a human-readable, localized message.
 *
 * Pass the result to `t()`: `t(getErrorMessageKey(error))`, or use
 * {@link useErrorMessage} / the `error` prop on `ReportErrorState`.
 */
/**
 * The ledger's own filter diagnostics (`directive-filter.ts`), forwarded as
 * BAD_USER_INPUT. They name which header filter failed, which the generic
 * "information provided is invalid" did not (w0/020). Only the category is
 * used; the server text itself is never shown.
 */
const TIME_FILTER_ERROR = /^Failed to parse date:/;
const ADVANCED_FILTER_ERROR =
  /^(?:Illegal character|Trailing tokens|Unexpected end of filter|Unexpected token|Expected .+, got|Expected : or comparison|Filter pattern exceeds)/;

export function getErrorMessageKey(error: unknown): string {
  if (CombinedGraphQLErrors.is(error)) {
    for (const gqlError of error.errors) {
      if (gqlError.extensions?.code !== "BAD_USER_INPUT") continue;
      if (TIME_FILTER_ERROR.test(gqlError.message)) {
        return "common.errors.invalidTimeFilter";
      }
      if (ADVANCED_FILTER_ERROR.test(gqlError.message)) {
        return "common.errors.invalidFilterExpression";
      }
    }
    for (const gqlError of error.errors) {
      const code = gqlError.extensions?.code;
      if (typeof code === "string" && code in ERROR_CODE_TO_KEY) {
        return ERROR_CODE_TO_KEY[code];
      }
    }
    return GENERIC_ERROR_KEY;
  }

  // Non-2xx / unparseable responses from the API gateway.
  if (ServerError.is(error) || ServerParseError.is(error)) {
    return "common.errors.serviceUnavailable";
  }

  // fetch() rejects with a TypeError when the network request itself fails
  // (offline, DNS, CORS) — before any server response exists. Only the known
  // per-browser fetch-failure messages are treated as network errors; any
  // other TypeError is almost certainly a programming bug and must not be
  // reported to the user as a connectivity problem.
  if (error instanceof TypeError && isFetchFailureMessage(error.message)) {
    return "common.errors.network";
  }

  return GENERIC_ERROR_KEY;
}

/**
 * The residual an UNBALANCED refusal names (`"1 USD"`, `"0.003 EUR, 1 JPY"`),
 * so an entry form can say how far off the postings are; `null` for any
 * other error.
 */
export function getUnbalancedResidual(error: unknown): string | null {
  if (!CombinedGraphQLErrors.is(error)) return null;
  for (const gqlError of error.errors) {
    const { code, residual } = gqlError.extensions ?? {};
    if (
      code === "UNBALANCED" &&
      typeof residual === "string" &&
      residual !== "" &&
      residual !== "unknown"
    ) {
      return residual;
    }
  }
  return null;
}

const NEW_LEDGER_ERRORS = /new bean-check errors?: ([\s\S]+)$/;

/**
 * What a would-break refusal names: entries that are valid on their own but
 * would add bean-check errors are refused as VALIDATION_FAILED on `entries`,
 * the reason ending with each new error (w0/m2). That text is the ledger's
 * own diagnostic — account names and file:line — so, like the UNBALANCED
 * residual, it is shown; `null` for any other error.
 */
export function getNewLedgerErrorDetail(error: unknown): string | null {
  if (!CombinedGraphQLErrors.is(error)) return null;
  for (const gqlError of error.errors) {
    const { code, field, reason } = gqlError.extensions ?? {};
    if (
      code !== "VALIDATION_FAILED" ||
      field !== "entries" ||
      typeof reason !== "string"
    ) {
      continue;
    }
    const detail = NEW_LEDGER_ERRORS.exec(reason)?.[1]?.trim();
    if (detail) return detail;
  }
  return null;
}

const FETCH_FAILURE_MESSAGES = [
  "failed to fetch", // Chromium
  "networkerror when attempting to fetch resource", // Firefox
  "load failed", // Safari
];

function isFetchFailureMessage(message: string): boolean {
  const normalized = message.toLowerCase();
  return FETCH_FAILURE_MESSAGES.some((pattern) => normalized.includes(pattern));
}

/**
 * Hook returning a stable formatter that resolves any error to a localized,
 * user-safe message string. Intended for imperative contexts (toasts,
 * mutation callbacks):
 *
 * ```tsx
 * const formatError = useErrorMessage();
 * mutate().catch((error) => toast.error(formatError(error)));
 * ```
 *
 * The returned function keeps a stable identity across renders (it reads the
 * latest `t` through a ref), so it is safe in effect/callback dependency
 * arrays without re-triggering them.
 */
export function useErrorMessage(): (error: unknown) => string {
  const { t } = useTranslations();
  const tRef = useRef(t);
  useEffect(() => {
    tRef.current = t;
  });
  return useCallback((error: unknown) => {
    const detail = getNewLedgerErrorDetail(error);
    return detail
      ? tRef.current("common.errors.wouldBreakLedger", { detail })
      : tRef.current(getErrorMessageKey(error));
  }, []);
}
