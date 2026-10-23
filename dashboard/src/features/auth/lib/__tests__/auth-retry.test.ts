import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { describe, expect, it } from "vitest";
import { readAuthRetry } from "../auth-retry";

const refusal = (...extensions: Record<string, unknown>[]) =>
  new CombinedGraphQLErrors({
    errors: extensions.map((value) => ({
      message: "synthetic private provider detail",
      extensions: value,
    })),
  });

describe("authentication retry metadata", () => {
  it("uses the longest eligible retry and identifies the rate-limited path", () => {
    expect(
      readAuthRetry(
        refusal(
          { code: "RATE_LIMITED", retryAfter: 2.1 },
          { code: "SERVICE_UNAVAILABLE", retryAfter: 5 },
          { code: "BAD_USER_INPUT", retryAfter: 999 },
        ),
      ),
    ).toEqual({ isRateLimited: true, retryAfter: 5 });
  });

  it("keeps a retryable outage distinct from account throttling", () => {
    expect(
      readAuthRetry(refusal({ code: "SERVICE_UNAVAILABLE", retryAfter: 5 })),
    ).toEqual({ isRateLimited: false, retryAfter: 5 });
  });

  it.each([undefined, "60", -1, 0, NaN, Infinity])(
    "ignores invalid retry values (%s)",
    (retryAfter) => {
      expect(
        readAuthRetry(refusal({ code: "RATE_LIMITED", retryAfter })),
      ).toEqual({ isRateLimited: true, retryAfter: undefined });
    },
  );

  it("rounds fractional delays and bounds hostile durations", () => {
    expect(
      readAuthRetry(refusal({ code: "RATE_LIMITED", retryAfter: 0.1 }))
        .retryAfter,
    ).toBe(1);
    expect(
      readAuthRetry(
        refusal({ code: "RATE_LIMITED", retryAfter: Number.MAX_VALUE }),
      ).retryAfter,
    ).toBe(86_400);
    expect(readAuthRetry(new Error("retryAfter=60 RATE_LIMITED"))).toEqual({
      isRateLimited: false,
    });
  });
});
