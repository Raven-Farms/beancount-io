import {
  PasswordPolicyError,
  passwordPolicyViolation,
} from "../password-policy";
import { ErrorCategory } from "@/shared/errors";

// The Kratos-style rule for a new password (w5): length in characters, bcrypt's
// byte cap, and distance from the account's identifiers. Cases marked Kratos
// come from ory/kratos selfservice/strategy/password/validator_test.go.

describe("passwordPolicyViolation", () => {
  it("refuses fewer than 8 characters and accepts 8", () => {
    expect(passwordPolicyViolation("7chars!", [])).toBe("MIN_LENGTH");
    expect(passwordPolicyViolation("8chars!!", [])).toBeNull();
  });

  it("caps bytes, not characters, at bcrypt's 72", () => {
    expect(passwordPolicyViolation("x".repeat(72), [])).toBeNull();
    expect(passwordPolicyViolation("x".repeat(73), [])).toBe("MAX_LENGTH");
    // "€" is three bytes: 24 fit, 25 do not, though both are under 72 characters.
    expect(passwordPolicyViolation("€".repeat(24), [])).toBeNull();
    expect(passwordPolicyViolation("€".repeat(25), [])).toBe("MAX_LENGTH");
  });

  it.each([
    ["hello@exam", "hello@example.com"], // Kratos
    ["HELLO@EXAMPLE.COM", "hello@example.com"], // Kratos: case-insensitive
    ["johnsmith1", "johnsmith@gmail.com"],
    ["kestrel2024", "kestrel"],
    ["kestre1!", "kestrel"],
  ])("refuses %j as too similar to %j", (password, identifier) => {
    expect(passwordPolicyViolation(password, [identifier])).toBe("TOO_SIMILAR");
  });

  it.each([
    ["9d3c8a1b", "abcd"], // Kratos
    ["plinth-orbit-mangle", "alice@example.com"],
    ["correct horse battery", "ana_99"],
  ])("accepts %j against %j", (password, identifier) => {
    expect(passwordPolicyViolation(password, [identifier])).toBeNull();
  });

  it("checks every identifier and skips empty ones", () => {
    expect(
      passwordPolicyViolation("kestrel2024", [
        "alice@example.com",
        null,
        undefined,
        "",
        "kestrel",
      ]),
    ).toBe("TOO_SIMILAR");
    expect(
      passwordPolicyViolation("plinth-orbit", [null, undefined, ""]),
    ).toBeNull();
  });
});

describe("PasswordPolicyError", () => {
  it("is a password-field validation failure naming the rule", () => {
    const error = new PasswordPolicyError("MAX_LENGTH");
    expect(error.category).toBe(ErrorCategory.VALIDATION_FAILED);
    expect(error.metadata).toMatchObject({
      field: "password",
      passwordPolicy: "MAX_LENGTH",
    });
    expect(error.metadata?.hint).toEqual(expect.any(String));
  });
});
