import {
  checkDirectiveLimitForFileChanges,
  countDirectivesForRepo,
} from "@/core/directive-limit";
import { countLedgerDirectives } from "@/foundation/rustledger";
import { resolveHeadShaCoalesced } from "@/foundation/clients/load-cached-ledger-file-map";
import { getMaxDirectives } from "@/core/backend-v2-limits";
import { RateLimitedError } from "@/shared/errors";

// A checked write used to parse the current ledger and the projected one on
// every write (w0/m5). The current count only decides a write past the limit
// (is it growing an already-over ledger, or crossing?), so a write within the
// limit now parses the projected ledger alone. Counts are also memoized by
// content inside countLedgerDirectives (count-ledger-directives.test.ts).

const warn = jest.fn();
jest.mock("@/shared/logger", () => ({
  logger: {
    child: () => ({
      warn: (...args: unknown[]) => warn(...args),
      info: jest.fn(),
      debug: jest.fn(),
      error: jest.fn(),
    }),
  },
}));

// One directive per dated line, so a count says which map it was given.
jest.mock("@/foundation/rustledger", () => ({
  ...jest.requireActual("@/foundation/rustledger"),
  countLedgerDirectives: jest.fn(
    async (files: Record<string, string>) =>
      Object.values(files)
        .join("\n")
        .split("\n")
        .filter((line) => /^\d{4}-\d{2}-\d{2} /u.test(line)).length,
  ),
}));

const MAIN =
  "2024-01-01 open Assets:Cash USD\n2024-01-02 open Assets:Bank USD\n";
jest.mock("@/foundation/clients/load-cached-ledger-file-map", () => ({
  loadCachedFileMapForRepo: jest.fn(async () => ({
    files: { "main.bean": MAIN },
    entryPoint: "main.bean",
    repoPaths: ["main.bean"],
    managedPrices: [],
    managedPricePaths: [],
  })),
  resolveHeadShaCoalesced: jest.fn(),
}));

jest.mock("@/core/backend-v2-limits", () => ({ getMaxDirectives: jest.fn() }));

const countMock = countLedgerDirectives as jest.Mock;
const headMock = resolveHeadShaCoalesced as jest.Mock;
const limitMock = getMaxDirectives as jest.Mock;

const base64 = (text: string) => Buffer.from(text).toString("base64");
const addOne = {
  "main.bean": base64(`${MAIN}2024-01-03 open Assets:Savings USD\n`),
};
const removeOne = { "main.bean": base64("2024-01-01 open Assets:Cash USD\n") };

/** What the counter returned, call by call: which map it was asked about. */
const countedSizes = async () =>
  (
    await Promise.allSettled(
      countMock.mock.results.map((result) => result.value),
    )
  ).map((outcome) =>
    outcome.status === "fulfilled" ? outcome.value : "refused",
  );

beforeEach(() => {
  countMock.mockClear();
  warn.mockClear();
  limitMock.mockResolvedValue(1000);
  headMock.mockResolvedValue("sha-a");
});

describe("which ledgers a checked write counts", () => {
  it("counts only the projected ledger for a write within the limit", async () => {
    await checkDirectiveLimitForFileChanges({} as never, "alice", "l", addOne);

    expect(await countedSizes()).toEqual([3]);
  });

  it("counts the current ledger too for a write past the limit, and refuses a growing one", async () => {
    limitMock.mockResolvedValue(2);

    await expect(
      checkDirectiveLimitForFileChanges({} as never, "alice", "l", addOne),
    ).rejects.toThrow(/free-tier limit of 2 directives .*approximately 3/u);
    expect(await countedSizes()).toEqual([3, 2]);
  });

  it("lets a shrinking write through on a ledger already over the limit", async () => {
    limitMock.mockResolvedValue(0);

    await expect(
      checkDirectiveLimitForFileChanges({} as never, "alice", "l", removeOne),
    ).resolves.toBeUndefined();
    expect(await countedSizes()).toEqual([1, 2]);
  });

  it("counts nothing for a paid ledger", async () => {
    limitMock.mockResolvedValue(-1);

    await checkDirectiveLimitForFileChanges({} as never, "alice", "l", addOne);

    expect(countMock).not.toHaveBeenCalled();
  });

  it("reports the committed count and its commit to the push gate", async () => {
    await expect(
      countDirectivesForRepo({} as never, "alice", "l"),
    ).resolves.toEqual({ count: 2, sha: "sha-a" });
  });

  it("lets the write through and logs it when the worker pool refuses the count", async () => {
    countMock.mockRejectedValueOnce(
      new RateLimitedError(1, "Ledger processing capacity is full."),
    );

    await expect(
      checkDirectiveLimitForFileChanges({} as never, "alice", "l", addOne),
    ).resolves.toBeUndefined();
    expect(warn).toHaveBeenCalledWith(
      "directive-limit pre-check failed open",
      expect.objectContaining({ owner: "alice", repoName: "l" }),
    );
  });
});
