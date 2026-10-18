import { describe, expect, it, vi } from "vitest";
import { CombinedGraphQLErrors } from "@apollo/client/errors";

vi.mock("@/common/apollo/client", () => ({ getClient: vi.fn() }));

import { fetchUserProfile } from "../user";

type ClientArg = Parameters<typeof fetchUserProfile>[0];

function clientWith(query: ReturnType<typeof vi.fn>): ClientArg {
  return { query } as unknown as ClientArg;
}

const graphQLError = (code: string) =>
  new CombinedGraphQLErrors({
    errors: [{ message: `error ${code}`, extensions: { code } }],
  });

describe("fetchUserProfile auth states (w3/646)", () => {
  it("reports signed-in when the query returns a profile", async () => {
    const profile = { id: "u1", email: "qa@example.com" };
    const client = clientWith(
      vi.fn(async () => ({ data: { userProfile: profile } })),
    );
    await expect(fetchUserProfile(client)).resolves.toEqual({
      status: "signed-in",
      profile,
    });
  });

  it("reports signed-out when an anonymous caller gets a null profile", async () => {
    const client = clientWith(
      vi.fn(async () => ({ data: { userProfile: null } })),
    );
    await expect(fetchUserProfile(client)).resolves.toEqual({
      status: "signed-out",
    });
  });

  it("reports signed-out on an UNAUTHENTICATED error", async () => {
    const client = clientWith(
      vi.fn(async () => {
        throw graphQLError("UNAUTHENTICATED");
      }),
    );
    await expect(fetchUserProfile(client)).resolves.toEqual({
      status: "signed-out",
    });
  });

  it.each([
    ["a 5xx GraphQL error", () => graphQLError("SERVICE_UNAVAILABLE")],
    ["an internal error", () => graphQLError("INTERNAL_SERVER_ERROR")],
    ["a network failure", () => new TypeError("Failed to fetch")],
    ["an unexpected failure", () => new Error("boom")],
  ])(
    "reports unavailable (not signed-out) on %s, keeping the error",
    async (_label, makeError) => {
      const error = makeError();
      const client = clientWith(
        vi.fn(async () => {
          throw error;
        }),
      );
      await expect(fetchUserProfile(client)).resolves.toEqual({
        status: "unavailable",
        error,
      });
    },
  );
});
