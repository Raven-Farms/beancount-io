import { describe, expect, it } from "vitest";
import { Route } from "../auth.login.index";

const parse = Route.options.validateSearch as (
  input: Record<string, unknown>,
) => Record<string, unknown>;
const recovery = `rcv_${"a".repeat(64)}`;

describe("the real login recovery route search contract", () => {
  it("keeps the mailed challenge and continuation fragment while stripping credential fields", () => {
    expect(
      parse({
        recovery,
        next: "/ledger/owner/book?view=journal#latest",
        email: "synthetic@example.com",
        code: "123456",
        password: "synthetic-password",
        token: "synthetic-token",
      }),
    ).toEqual({ recovery, next: "/ledger/owner/book?view=journal#latest" });
  });

  it.each([
    true,
    123,
    [],
    {},
    null,
    "aem_public-receipt",
    "rcv_short",
    `rcv_${"A".repeat(64)}`,
    `rcv_${"a".repeat(65)}`,
  ])(
    "drops malformed challenges without breaking ordinary login (%j)",
    (value) => {
      expect(
        parse({
          recovery: value,
          next: "/settings#profile",
          reason: "expired",
        }),
      ).toEqual({
        recovery: undefined,
        next: "/settings#profile",
        reason: "expired",
      });
    },
  );
});
