import { CombinedGraphQLErrors, ServerError } from "@apollo/client/errors";
import { describe, expect, it } from "vitest";
import enBql from "../../locales/en";
import { getQueryErrorFeedback } from "../query-error";

function graphQLError(message: string, code: string) {
  return new CombinedGraphQLErrors({
    errors: [{ message, extensions: { code } }],
  });
}

const UNKNOWN_COLUMN_MESSAGE =
  "Invalid BQL query: Query execution error: column 'nonexistent_column' not found";

describe("getQueryErrorFeedback", () => {
  it("names the column from the engine's unknown-column diagnostic", () => {
    expect(
      getQueryErrorFeedback(
        graphQLError(UNKNOWN_COLUMN_MESSAGE, "BAD_USER_INPUT"),
      ),
    ).toEqual({
      key: "bql.errors.unknownColumn",
      params: { column: "nonexistent_column" },
    });
  });

  it("has an English message that shows the column", () => {
    expect(enBql["bql.errors.unknownColumn"].message).toContain("{column}");
  });

  it("names the unexpected token and its 1-based position for a syntax error", () => {
    expect(
      getQueryErrorFeedback(
        graphQLError(
          "Invalid BQL query: syntax error at position 16: unexpected token 'FROM'",
          "BAD_USER_INPUT",
        ),
      ),
    ).toEqual({
      key: "bql.errors.syntaxError",
      params: { token: "FROM", position: "17" },
    });
    expect(
      getQueryErrorFeedback(
        graphQLError(
          "Invalid BQL query: syntax error at position 0: unexpected token 'SELEC'",
          "BAD_USER_INPUT",
        ),
      ),
    ).toEqual({
      key: "bql.errors.syntaxError",
      params: { token: "SELEC", position: "1" },
    });
  });

  it("has an English syntax message that shows the token and position", () => {
    const message = enBql["bql.errors.syntaxError"].message;
    expect(message).toContain("{token}");
    expect(message).toContain("{position}");
  });

  it("keeps generic feedback for other bad-input diagnostics", () => {
    for (const message of [
      "Invalid BQL query: syntax error at 'FROM'",
      "Invalid BQL query: Query execution error: type error: cannot compare values",
      "Invalid BQL query: syntax error at position 3: unexpected token '<img src=x>'",
      "Invalid BQL query: syntax error at position 3: unexpected token 'a'b'",
    ]) {
      expect(
        getQueryErrorFeedback(graphQLError(message, "BAD_USER_INPUT")),
      ).toEqual({ key: "common.errors.badUserInput" });
    }
  });

  it("ignores the diagnostic shape outside BAD_USER_INPUT", () => {
    expect(
      getQueryErrorFeedback(
        graphQLError(UNKNOWN_COLUMN_MESSAGE, "INTERNAL_SERVER_ERROR"),
      ),
    ).toEqual({ key: "common.errors.internal" });
    expect(
      getQueryErrorFeedback(
        graphQLError(UNKNOWN_COLUMN_MESSAGE, "SERVICE_UNAVAILABLE"),
      ),
    ).toEqual({ key: "common.errors.serviceUnavailable" });
  });

  it("never interpolates an HTML-like or non-identifier column", () => {
    for (const column of ["<img src=x onerror=alert(1)>", "a b", "x'y", ""]) {
      expect(
        getQueryErrorFeedback(
          graphQLError(`column '${column}' not found`, "BAD_USER_INPUT"),
        ),
      ).toEqual({ key: "common.errors.badUserInput" });
    }
  });

  it("falls back for non-GraphQL failures", () => {
    expect(getQueryErrorFeedback(new Error(UNKNOWN_COLUMN_MESSAGE))).toEqual({
      key: "common.errors.generic",
    });
    expect(
      getQueryErrorFeedback(
        new ServerError("bad gateway", {
          response: new Response(null, { status: 502 }),
          bodyText: "",
        }),
      ),
    ).toEqual({ key: "common.errors.serviceUnavailable" });
  });
});
