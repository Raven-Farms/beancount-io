import { describe, expect, it } from "vitest";
import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { isUnknownCliCodeError } from "../cli-auth-errors";
import enAuth from "@/features/auth/locales/en";

const graphQLError = (message: string, code: string) =>
  new CombinedGraphQLErrors({ errors: [{ message, extensions: { code } }] });

describe("unknown CLI code errors (w0/019)", () => {
  it("recognizes the server's unknown-or-expired session answer", () => {
    expect(
      isUnknownCliCodeError(
        graphQLError("CLI auth session not found or expired", "BAD_USER_INPUT"),
      ),
    ).toBe(true);
  });

  it("leaves other bad input, service failures and non-GraphQL errors generic", () => {
    expect(
      isUnknownCliCodeError(
        graphQLError("Invalid code shape", "BAD_USER_INPUT"),
      ),
    ).toBe(false);
    expect(
      isUnknownCliCodeError(
        graphQLError(
          "CLI auth session not found or expired",
          "INTERNAL_SERVER_ERROR",
        ),
      ),
    ).toBe(false);
    expect(isUnknownCliCodeError(new Error("not found or expired"))).toBe(
      false,
    );
  });

  it("tells the user to rerun bea login", () => {
    expect(enAuth["auth.cliAuthCodeUnknown"].message).toContain("bea login");
  });
});
