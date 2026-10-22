import { ZodError, z } from "zod";
import { toErrorResponse } from "@/server/error-middleware";
import {
  BadUserInputError,
  DomainError,
  ErrorCategory,
  NotFoundError,
} from "@/shared/errors";

describe("toErrorResponse", () => {
  it("maps DomainError categories to Python-compatible status + envelope", () => {
    const notFound = toErrorResponse(new NotFoundError("Repo"));
    expect(notFound.status).toBe(404);
    expect(notFound.body).toEqual({
      success: false,
      error: "Repo not found",
      code: null,
      details: null,
    });

    const badInput = toErrorResponse(new BadUserInputError("bad name"));
    expect(badInput.status).toBe(400);
  });

  it("surfaces structured code/details from error metadata (directive limit)", () => {
    class StructuredError extends DomainError {}
    const err = new StructuredError(
      ErrorCategory.RESOURCE_LIMIT_REACHED,
      "Directive limit exceeded",
      {
        code: "directive_limit_exceeded",
        details: { limit: 1000, current: 1005 },
      },
    );
    const res = toErrorResponse(err);
    expect(res.status).toBe(403);
    expect(res.body).toEqual({
      success: false,
      error: "Directive limit exceeded",
      code: "directive_limit_exceeded",
      details: { limit: 1000, current: 1005 },
    });
  });

  it("maps zod validation failures to the Python 422 message format", () => {
    let zodError: ZodError | undefined;
    try {
      z.object({ query: z.string() }).parse({});
    } catch (e) {
      zodError = e as ZodError;
    }
    const res = toErrorResponse(zodError);
    expect(res.status).toBe(422);
    expect(res.body.error).toMatch(/^Validation error: query: /);
  });

  it("forwards Gitea HTTP errors with the Gitea body message", () => {
    const res = toErrorResponse({
      status: 404,
      error: { message: "user does not exist" },
    });
    expect(res.status).toBe(404);
    expect(res.body.error).toBe("user does not exist");
  });

  it("preserves empty-string Gitea messages (explicit None check parity)", () => {
    const res = toErrorResponse({ status: 409, error: { message: "" } });
    expect(res.status).toBe(409);
    expect(res.body.error).toBe("");
  });

  // w23/017: the loser of two concurrent commits got Gitea's raw 500, which
  // backend-v2 reported as "dependency down".
  it("answers a commit that lost the branch-ref race with 409", () => {
    const lost = toErrorResponse({
      status: 500,
      error: {
        message:
          "PushRejected Error: exit status 1 - remote: error: cannot lock ref 'refs/heads/main': is at 4085f06 but expected d3b78fe",
      },
    });
    expect(lost.status).toBe(409);
    expect(lost.body.error).toContain("concurrent write");

    const otherFailure = toErrorResponse({
      status: 500,
      error: { message: "PushRejected Error: pre-receive hook declined" },
    });
    expect(otherFailure.status).toBe(500);
  });

  // w23/032: Gitea answers these with 422, which backend-v2 read as the
  // caller's bad input instead of the documented 409 CONFLICT.
  it("answers a stale sha with 409 and a retry", () => {
    const stale = toErrorResponse({
      status: 422,
      error: { message: "sha does not match [given: abc, expected: def]" },
    });
    expect(stale.status).toBe(409);
    expect(stale.body.error).toBe(
      "the ledger changed under a concurrent write; re-read it and retry",
    );
  });

  it("answers a create over an existing file with 409 naming it", () => {
    const taken = toErrorResponse({
      status: 422,
      error: { message: "repository file already exists [path: qa.bean]" },
    });
    expect(taken.status).toBe(409);
    expect(taken.body.error).toBe(
      "qa.bean already exists; update it with its sha, or choose another path",
    );
  });

  it("keeps any other 422 a 422 with Gitea's message", () => {
    const invalid = toErrorResponse({
      status: 422,
      error: { message: "path contains a malformed path component" },
    });
    expect(invalid.status).toBe(422);
    expect(invalid.body.error).toBe("path contains a malformed path component");
  });

  it("falls back to 500 Internal server error for unknown throwables", () => {
    const res = toErrorResponse(new Error("boom"));
    expect(res.status).toBe(500);
    expect(res.body).toEqual({
      success: false,
      error: "Internal server error",
      code: null,
      details: null,
    });
  });
});
