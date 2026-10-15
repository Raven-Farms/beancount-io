import { describe, expect, it, vi } from "vitest";
import { isNotFound, isRedirect } from "@tanstack/react-router";
import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { Route } from "../ledger_assets.$ledgerRepoId.static.$";

type BeforeLoad = (options: {
  context: { client: { query: ReturnType<typeof vi.fn> } };
  params: { ledgerRepoId: string; _splat?: string };
}) => Promise<unknown>;

const beforeLoad = Route.options.beforeLoad as unknown as BeforeLoad;

async function outcome(
  params: { ledgerRepoId: string; _splat?: string },
  query: ReturnType<typeof vi.fn>,
) {
  try {
    await beforeLoad({ context: { client: { query } }, params });
    return "returned";
  } catch (thrown) {
    if (isNotFound(thrown)) return "notFound";
    if (isRedirect(thrown)) return "redirect";
    return "error";
  }
}

const graphQLError = (code: string) =>
  new CombinedGraphQLErrors({
    errors: [{ message: "Ledger not found", extensions: { code } }],
  });

describe("ledger asset links (w0/018)", () => {
  it("answers 404 for a malformed repo id without calling the API", async () => {
    const query = vi.fn();
    expect(await outcome({ ledgerRepoId: "abc", _splat: "x" }, query)).toBe(
      "notFound",
    );
    expect(query).not.toHaveBeenCalled();
  });

  it("answers 404 when the ledger or file is missing or forbidden", async () => {
    for (const code of ["NOT_FOUND", "FORBIDDEN"]) {
      const query = vi.fn().mockRejectedValue(graphQLError(code));
      expect(
        await outcome({ ledgerRepoId: "7", _splat: "r.png" }, query),
        code,
      ).toBe("notFound");
    }
  });

  it("keeps real failures and the signed-out redirect path as errors", async () => {
    const query = vi.fn().mockRejectedValue(graphQLError("UNAUTHENTICATED"));
    expect(await outcome({ ledgerRepoId: "7", _splat: "r.png" }, query)).toBe(
      "error",
    );
  });

  it("redirects to the signed download URL when one exists", async () => {
    const query = vi.fn().mockResolvedValue({
      data: {
        getLedgerAssetDownloadUrl: { downloadUrl: "https://s.example/r" },
      },
    });
    expect(await outcome({ ledgerRepoId: "7", _splat: "r.png" }, query)).toBe(
      "redirect",
    );
  });
});
