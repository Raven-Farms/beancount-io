import { describe, expect, it } from "vitest";
import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { newPasswordSchema, passwordPolicyRefusalKey } from "../password-rule";

// The key stands in for its message, so a failure names the rule it broke.
const schema = newPasswordSchema((key: string) => key);
const refusalOf = (password: string) =>
  schema.safeParse(password).error?.issues[0]?.message ?? null;

describe("newPasswordSchema", () => {
  it("requires 8 characters, as backend-v2 does", () => {
    expect(refusalOf("")).toBe("auth.newPasswordRequired");
    expect(refusalOf("seven77")).toBe("auth.newPasswordMinLength");
    expect(refusalOf("eight888")).toBeNull();
  });

  it("caps UTF-8 bytes, not characters, at bcrypt's 72", () => {
    expect(refusalOf("x".repeat(72))).toBeNull();
    expect(refusalOf("x".repeat(73))).toBe("auth.newPasswordMaxLength");
    // Three bytes each: 24 fit and 25 do not, both under 72 characters.
    expect(refusalOf("€".repeat(24))).toBeNull();
    expect(refusalOf("€".repeat(25))).toBe("auth.newPasswordMaxLength");
  });
});

const refusal = (extensions: Record<string, unknown>) =>
  new CombinedGraphQLErrors({
    errors: [{ message: "Validation failed for password: …", extensions }],
  });

describe("passwordPolicyRefusalKey", () => {
  it.each([
    ["BREACHED", "auth.passwordBreached"],
    ["TOO_SIMILAR", "auth.passwordTooSimilar"],
    ["MIN_LENGTH", "auth.newPasswordMinLength"],
    ["MAX_LENGTH", "auth.newPasswordMaxLength"],
  ])("names %s refusals with %s", (rule, key) => {
    expect(
      passwordPolicyRefusalKey(
        refusal({
          code: "VALIDATION_FAILED",
          field: "password",
          passwordPolicy: rule,
        }),
      ),
    ).toBe(key);
  });

  it("leaves every other error to the shared messages", () => {
    expect(
      passwordPolicyRefusalKey(refusal({ code: "VALIDATION_FAILED" })),
    ).toBeNull();
    expect(
      passwordPolicyRefusalKey(refusal({ passwordPolicy: "toString" })),
    ).toBeNull();
    expect(passwordPolicyRefusalKey(new Error("offline"))).toBeNull();
  });
});
