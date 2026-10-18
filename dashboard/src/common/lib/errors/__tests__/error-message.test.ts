import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { CombinedGraphQLErrors, ServerError } from "@apollo/client/errors";
import {
  getErrorMessageKey,
  getNewLedgerErrorDetail,
  getUnbalancedResidual,
  useErrorMessage,
} from "../error-message";

function graphQLError(code?: string): CombinedGraphQLErrors {
  return new CombinedGraphQLErrors({
    errors: [
      {
        message: "raw internal server message",
        ...(code ? { extensions: { code } } : {}),
      },
    ],
  });
}

describe("getErrorMessageKey", () => {
  it.each([
    ["UNAUTHENTICATED", "common.errors.unauthenticated"],
    ["FORBIDDEN", "common.errors.forbidden"],
    ["NOT_FOUND", "common.errors.notFound"],
    ["BAD_USER_INPUT", "common.errors.badUserInput"],
    ["VALIDATION_FAILED", "common.errors.validationFailed"],
    ["CONFLICT", "common.errors.conflict"],
    ["RATE_LIMITED", "common.errors.rateLimited"],
    ["INTERNAL_SERVER_ERROR", "common.errors.internal"],
    ["SERVICE_UNAVAILABLE", "common.errors.serviceUnavailable"],
    ["RESOURCE_LIMIT_REACHED", "common.errors.resourceLimitReached"],
    ["OPERATION_NOT_ALLOWED", "common.errors.operationNotAllowed"],
    ["PREMIUM_REQUIRED", "common.errors.premiumRequired"],
    ["UNBALANCED", "common.errors.unbalanced"],
  ])("maps GraphQL extensions.code %s to %s", (code, expectedKey) => {
    expect(getErrorMessageKey(graphQLError(code))).toBe(expectedKey);
  });

  it("falls back to the generic key for unknown GraphQL error codes", () => {
    expect(getErrorMessageKey(graphQLError("SOME_NEW_CODE"))).toBe(
      "common.errors.generic",
    );
  });

  it("falls back to the generic key when a GraphQL error has no code", () => {
    expect(getErrorMessageKey(graphQLError())).toBe("common.errors.generic");
  });

  it("uses the first recognized code among multiple GraphQL errors", () => {
    const error = new CombinedGraphQLErrors({
      errors: [
        { message: "no code here" },
        { message: "forbidden", extensions: { code: "FORBIDDEN" } },
      ],
    });
    expect(getErrorMessageKey(error)).toBe("common.errors.forbidden");
  });

  it("maps server (non-2xx) responses to the service-unavailable key", () => {
    const error = new ServerError("Bad Gateway", {
      response: new Response(null, { status: 502 }),
      bodyText: "",
    });
    expect(getErrorMessageKey(error)).toBe("common.errors.serviceUnavailable");
  });

  it.each([
    "Failed to fetch",
    "NetworkError when attempting to fetch resource.",
    "Load failed",
  ])("maps the fetch-failure TypeError %j to the network key", (message) => {
    expect(getErrorMessageKey(new TypeError(message))).toBe(
      "common.errors.network",
    );
  });

  it("maps programming-bug TypeErrors to the generic key, not network", () => {
    expect(
      getErrorMessageKey(
        new TypeError("Cannot read properties of undefined (reading 'foo')"),
      ),
    ).toBe("common.errors.generic");
    expect(getErrorMessageKey(new TypeError("x is not a function"))).toBe(
      "common.errors.generic",
    );
  });

  it("maps plain errors, strings, and undefined to the generic key", () => {
    expect(getErrorMessageKey(new Error("boom"))).toBe("common.errors.generic");
    expect(getErrorMessageKey("boom")).toBe("common.errors.generic");
    expect(getErrorMessageKey(undefined)).toBe("common.errors.generic");
  });
});

describe("header filter diagnostics (w0/020)", () => {
  const badInput = (message: string, code = "BAD_USER_INPUT") =>
    new CombinedGraphQLErrors({ errors: [{ message, extensions: { code } }] });

  it("names the Time filter when the period cannot be parsed", () => {
    expect(
      getErrorMessageKey(badInput("Failed to parse date: last mnth")),
    ).toBe("common.errors.invalidTimeFilter");
  });

  it("names the filter expression for its parser errors", () => {
    for (const message of [
      'Illegal character """',
      "Trailing tokens",
      "Unexpected end of filter",
      "Unexpected token RPAREN",
      "Expected STRING, got EOF",
    ]) {
      expect(getErrorMessageKey(badInput(message)), message).toBe(
        "common.errors.invalidFilterExpression",
      );
    }
  });

  it("keeps the generic bad-input message for other diagnostics and codes", () => {
    expect(getErrorMessageKey(badInput("Ledger option missing"))).toBe(
      "common.errors.badUserInput",
    );
    expect(
      getErrorMessageKey(
        badInput("Failed to parse date: x", "INTERNAL_SERVER_ERROR"),
      ),
    ).toBe("common.errors.internal");
  });
});

describe("getUnbalancedResidual", () => {
  const refusal = (extensions: Record<string, unknown>) =>
    new CombinedGraphQLErrors({
      errors: [{ message: "entry 0: does not balance", extensions }],
    });

  it("returns the residual an UNBALANCED refusal names", () => {
    expect(
      getUnbalancedResidual(
        refusal({ code: "UNBALANCED", residual: "0.003 EUR, 1 JPY" }),
      ),
    ).toBe("0.003 EUR, 1 JPY");
  });

  it.each([
    ["another code", { code: "VALIDATION_FAILED", residual: "1 USD" }],
    ["no residual", { code: "UNBALANCED" }],
    ["an unparsed residual", { code: "UNBALANCED", residual: "unknown" }],
  ])("returns null for %s", (_case, extensions) => {
    expect(getUnbalancedResidual(refusal(extensions))).toBeNull();
  });

  it("returns null for errors that are not GraphQL refusals", () => {
    expect(getUnbalancedResidual(new Error("UNBALANCED"))).toBeNull();
  });
});

// Entries that would add bean-check errors are refused as VALIDATION_FAILED on
// `entries`, the reason naming each new error (w0/m2). The forms say what the
// write would break instead of "Validation failed".
describe("would-break refusals", () => {
  const refusal = (extensions: Record<string, unknown>) =>
    new CombinedGraphQLErrors({
      errors: [
        {
          message: `Validation failed for entries: ${String(extensions.reason)}`,
          extensions,
        },
      ],
    });
  const wouldBreak = (detail: string, count = 1) =>
    refusal({
      code: "VALIDATION_FAILED",
      field: "entries",
      reason: `adding these entries would introduce ${count} new bean-check error${count === 1 ? "" : "s"}: ${detail}`,
    });

  it("names the error a refused write would add", () => {
    expect(
      getNewLedgerErrorDetail(
        wouldBreak("Duplicate open directive for Assets:Cash (main.bean:74)"),
      ),
    ).toBe("Duplicate open directive for Assets:Cash (main.bean:74)");
    expect(
      getNewLedgerErrorDetail(
        wouldBreak("A (main.bean:1); B (main.bean:2)", 2),
      ),
    ).toBe("A (main.bean:1); B (main.bean:2)");
  });

  it.each([
    [
      "another field",
      {
        code: "VALIDATION_FAILED",
        field: "username",
        reason: "1 new bean-check error: X",
      },
    ],
    [
      "another code",
      {
        code: "BAD_USER_INPUT",
        field: "entries",
        reason: "1 new bean-check error: X",
      },
    ],
    [
      "another entries refusal",
      { code: "VALIDATION_FAILED", field: "entries", reason: "Must be set" },
    ],
  ])("returns null for %s", (_case, extensions) => {
    expect(getNewLedgerErrorDetail(refusal(extensions))).toBeNull();
  });

  it("returns null for errors that are not GraphQL refusals", () => {
    expect(
      getNewLedgerErrorDetail(new Error("1 new bean-check error: X")),
    ).toBeNull();
  });

  it("formats the refusal with what it would break", () => {
    const { result } = renderHook(() => useErrorMessage());
    expect(
      result.current(
        wouldBreak("Duplicate open directive for Assets:Cash (main.bean:74)"),
      ),
    ).toBe(
      "This would add an error to your ledger: Duplicate open directive for Assets:Cash (main.bean:74)",
    );
    expect(
      result.current(
        refusal({
          code: "VALIDATION_FAILED",
          field: "entries",
          reason: "Must be set",
        }),
      ),
    ).toBe("Validation failed. Please review your input and try again.");
  });
});
