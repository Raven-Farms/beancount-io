import {
  checkDirectiveLimitForFileChanges,
  countDirectivesForRepo,
} from "@/core/directive-limit";
import { countLedgerDirectives } from "@/foundation/rustledger";
import { resolveHeadShaCoalesced } from "@/foundation/clients/load-cached-ledger-file-map";
import { getMaxDirectives } from "@/core/backend-v2-limits";
import { RateLimitedError } from "@/shared/errors";

// A checked write used to parse the current ledger and the projected one, so a
// stream of small writes to a large ledger reparsed the same commit every time
// (w0/m5). The current count is now reused per commit; only the projected
// ledger is new work.

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

const addOne = {
  "main.bean": Buffer.from(
    `${MAIN}2024-01-03 open Assets:Savings USD\n`,
  ).toString("base64"),
};

/** The maps the counter was asked about, by how many directives they hold. */
const countedSizes = () =>
  countMock.mock.calls
    .map(([files]) =>
      Object.values(files as Record<string, string>)
        .join("\n")
        .split("\n")
        .filter((line) => /^\d{4}-/u.test(line)),
    )
    .map((lines) => lines.length);

let repo = 0;
const nextRepo = () => `ledger${++repo}`;

beforeEach(() => {
  countMock.mockClear();
  warn.mockClear();
  limitMock.mockResolvedValue(1000);
  headMock.mockResolvedValue("sha-a");
});

describe("directive count per commit", () => {
  it("counts the current commit once across writes against it", async () => {
    const name = nextRepo();

    await checkDirectiveLimitForFileChanges({} as never, "alice", name, addOne);
    await checkDirectiveLimitForFileChanges({} as never, "alice", name, addOne);

    // Current (2) once, projected (3) per write.
    expect(countedSizes()).toEqual([2, 3, 3]);
  });

  it("counts again once a push moves HEAD", async () => {
    const name = nextRepo();

    await checkDirectiveLimitForFileChanges({} as never, "alice", name, addOne);
    headMock.mockResolvedValue("sha-b");
    await checkDirectiveLimitForFileChanges({} as never, "alice", name, addOne);

    expect(countedSizes()).toEqual([2, 3, 2, 3]);
  });

  it("shares the count with the push gate's directive-count", async () => {
    const name = nextRepo();

    await expect(
      countDirectivesForRepo({} as never, "alice", name),
    ).resolves.toEqual({ count: 2, sha: "sha-a" });
    await checkDirectiveLimitForFileChanges({} as never, "alice", name, addOne);

    expect(countedSizes()).toEqual([2, 3]);
  });

  it("does not share a count between repositories at the same commit", async () => {
    await countDirectivesForRepo({} as never, "alice", nextRepo());
    await countDirectivesForRepo({} as never, "bob", nextRepo());

    expect(countedSizes()).toEqual([2, 2]);
  });

  it("lets the write through and logs it when the worker pool refuses the count", async () => {
    const name = nextRepo();
    countMock.mockRejectedValueOnce(
      new RateLimitedError(1, "Ledger processing capacity is full."),
    );

    await expect(
      checkDirectiveLimitForFileChanges({} as never, "alice", name, addOne),
    ).resolves.toBeUndefined();
    expect(warn).toHaveBeenCalledWith(
      "directive-limit pre-check failed open",
      expect.objectContaining({ owner: "alice", repoName: name }),
    );
  });

  it("does not remember a refused count", async () => {
    const name = nextRepo();
    countMock.mockRejectedValueOnce(new Error("worker timed out"));

    await checkDirectiveLimitForFileChanges({} as never, "alice", name, addOne);
    await checkDirectiveLimitForFileChanges({} as never, "alice", name, addOne);

    // The second write counts the commit itself instead of reusing a failure.
    expect(countedSizes()).toEqual([2, 2, 3]);
  });
});
