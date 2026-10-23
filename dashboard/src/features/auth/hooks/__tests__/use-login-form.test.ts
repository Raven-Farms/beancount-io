import { describe, expect, it } from "vitest";
import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { signInRefusalKey } from "../use-login-form";

// Every password sign-in form (login, OAuth consent, mobile consent) shows the
// message this picks. A spent per-account budget (w0/m7) answers RATE_LIMITED,
// and the shared "wait a moment" understates a 15-minute window.

const refusal = (code: string) =>
  new CombinedGraphQLErrors({
    errors: [{ message: "refused", extensions: { code } }],
  });

describe("signInRefusalKey", () => {
  it("says how to get out of a rate-limited sign-in", () => {
    expect(signInRefusalKey(refusal("RATE_LIMITED"))).toBe(
      "auth.loginRateLimited",
    );
  });

  it("keeps the login-failed message for rejected credentials", () => {
    expect(signInRefusalKey(refusal("UNAUTHENTICATED"))).toBe(
      "auth.loginFailed",
    );
  });

  it("leaves other refusals to the shared error messages", () => {
    expect(signInRefusalKey(refusal("SERVICE_UNAVAILABLE"))).toBeNull();
    expect(signInRefusalKey(new TypeError("Failed to fetch"))).toBeNull();
  });
});
