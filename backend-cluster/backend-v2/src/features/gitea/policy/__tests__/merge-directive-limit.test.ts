import {
  evaluateMergeDirectiveLimit,
  type DirectiveLimitGateDeps,
} from "../directive-limit-gate";

// A pull request merge used to bypass the directive limit entirely (w0/m6):
// any amount could be added through a branch and merged. The merge check asks
// what the merged ledger would hold — HEAD plus what the branch added since it
// left the base — and refuses only a merge that ends over the limit and bigger.

jest.mock("@/features/stripe/operations/get-user-tier", () => ({
  getUserTierLimits: jest.fn(),
}));
import { getUserTierLimits } from "@/features/stripe/operations/get-user-tier";
const tier = getUserTierLimits as jest.Mock;

const COMMITS = { head: "head000", mergeBase: "base000" };

/** Directive counts by ref; HEAD is the count with no ref. */
function deps(counts: { HEAD: number; head000: number; base000: number }) {
  const request = jest.fn(async (params: { query?: { ref?: string } }) => {
    const ref = params.query?.ref ?? "HEAD";
    return {
      data: {
        success: true,
        data: { count: counts[ref as keyof typeof counts], sha: ref },
      },
    };
  });
  const d: DirectiveLimitGateDeps = {
    models: {
      user: { getUserByUsername: jest.fn(async () => ({ id: "u_1" })) },
      paidCustomer: {},
    } as never,
    db: {} as never,
    stripe: {} as never,
    cacheHelper: { get: jest.fn(async () => false) } as never,
    ledgerClient: { request } as never,
  };
  return { d, request };
}

beforeEach(() => {
  jest.clearAllMocks();
  tier.mockResolvedValue({ maxDirectives: 100 });
});

describe("evaluateMergeDirectiveLimit", () => {
  it("refuses a merge that takes the ledger past the limit", async () => {
    // The branch adds 30 directives to a ledger of 80.
    const { d } = deps({ HEAD: 80, head000: 110, base000: 80 });

    await expect(
      evaluateMergeDirectiveLimit(d, "alice", "books", COMMITS),
    ).resolves.toEqual({ decision: "over", count: 110, limit: 100 });
  });

  it("allows a merge that stays within the limit", async () => {
    const { d } = deps({ HEAD: 80, head000: 95, base000: 80 });

    await expect(
      evaluateMergeDirectiveLimit(d, "alice", "books", COMMITS),
    ).resolves.toEqual({ decision: "under", count: 95, limit: 100 });
  });

  it("counts what the base gained since the branch left it", async () => {
    // The branch adds 15, which fits the base it started from (80 → 95), but
    // the base has since grown to 90, so the merge lands at 105.
    const { d } = deps({ HEAD: 90, head000: 95, base000: 80 });

    await expect(
      evaluateMergeDirectiveLimit(d, "alice", "books", COMMITS),
    ).resolves.toEqual({ decision: "over", count: 105, limit: 100 });
  });

  it("allows a shrinking merge on a ledger already over the limit", async () => {
    const { d } = deps({ HEAD: 150, head000: 140, base000: 150 });

    await expect(
      evaluateMergeDirectiveLimit(d, "alice", "books", COMMITS),
    ).resolves.toEqual({ decision: "under", count: 140, limit: 100 });
  });

  it("asks the ledger service for HEAD, the head and the merge base", async () => {
    const { d, request } = deps({ HEAD: 1, head000: 1, base000: 1 });

    await evaluateMergeDirectiveLimit(d, "alice", "books", COMMITS);

    const refs = request.mock.calls.map(([params]) => params.query?.ref);
    expect(refs.sort()).toEqual([undefined, "base000", "head000"].sort());
    for (const [params] of request.mock.calls) {
      expect(params).toMatchObject({
        path: "/ledgers/alice/books/directive-count",
        method: "GET",
      });
    }
  });

  it("counts nothing for an unlimited ledger", async () => {
    tier.mockResolvedValue({ maxDirectives: -1 });
    const { d, request } = deps({ HEAD: 1, head000: 1000, base000: 1 });

    await expect(
      evaluateMergeDirectiveLimit(d, "alice", "books", COMMITS),
    ).resolves.toEqual({ decision: "unlimited" });
    expect(request).not.toHaveBeenCalled();
  });

  it("fails open when a count fails", async () => {
    const { d, request } = deps({ HEAD: 1, head000: 1000, base000: 1 });
    request.mockRejectedValueOnce(new Error("ECONNREFUSED"));

    await expect(
      evaluateMergeDirectiveLimit(d, "alice", "books", COMMITS),
    ).resolves.toEqual({
      decision: "unknown",
      reason: expect.stringContaining("ECONNREFUSED"),
    });
  });
});
