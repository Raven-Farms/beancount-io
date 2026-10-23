import { describe, expect, it } from "vitest";
import { createLocalization } from "@/i18n/init";
import { Route } from "../auth.login.index";

const parse = Route.options.validateSearch as (
  input: Record<string, unknown>,
) => Record<string, unknown>;
const recovery = `rcv_${"a".repeat(64)}`;
const head = Route.options.head as (input: {
  match: {
    context: { localization: ReturnType<typeof createLocalization> };
    search: Record<string, unknown>;
  };
}) => { meta: Array<Record<string, string>> };

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

  it.each([undefined, "rcv_short", recovery])(
    "keeps only a valid recovery link out of search and referrers (%s)",
    (challenge) => {
      const metadata = head({
        match: {
          context: { localization: createLocalization() },
          search: parse({ recovery: challenge }),
        },
      });
      expect(metadata.meta).toContainEqual({
        title: "Sign In to Beancount — Free Plain-Text Accounting",
      });
      const privateMeta = metadata.meta.filter(
        (item) => item.name === "robots" || item.name === "referrer",
      );
      expect(privateMeta).toEqual(
        challenge === recovery
          ? [
              { name: "robots", content: "noindex, follow" },
              { name: "referrer", content: "no-referrer" },
            ]
          : [],
      );
      expect(JSON.stringify(metadata)).not.toContain(recovery);
    },
  );
});
