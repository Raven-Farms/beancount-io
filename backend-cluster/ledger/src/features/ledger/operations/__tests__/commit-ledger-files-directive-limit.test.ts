import { commitLedgerFiles } from "@/features/ledger/operations/commit-ledger-files";
import { getMaxDirectives } from "@/core/backend-v2-limits";
import { countLedgerDirectives } from "@/foundation/rustledger";

// Every commit through commitLedgerFiles is held to the free-tier directive
// limit (w0/m6). Source-slice updates used to commit with no check at all, so
// one entry could be replaced with any number of directives. The real check
// runs here; only its inputs are stubbed: the tier limit, the committed map
// (read from the same fake repository the commit writes to) and a counter that
// counts dated lines.

const remote: Record<string, string> = {};

jest.mock("@/core/backend-v2-limits", () => ({ getMaxDirectives: jest.fn() }));

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

jest.mock("@/foundation/clients/load-cached-ledger-file-map", () => ({
  loadCachedFileMapForRepo: jest.fn(async () => ({
    files: { ...remote },
    entryPoint: "main.bean",
    repoPaths: Object.keys(remote),
    managedPrices: [],
    managedPricePaths: [],
  })),
  resolveHeadShaCoalesced: jest.fn(async () => "head"),
}));

const limitMock = getMaxDirectives as jest.Mock;
const countMock = countLedgerDirectives as jest.Mock;

const conflict = Object.assign(new Error("sha mismatch"), { status: 409 });

/** A Gitea client over `remote`; `beforeCommit` runs before each commit lands. */
function repository(beforeCommit?: (attempt: number) => void) {
  let attempt = 0;
  const commits: Array<Record<string, string>> = [];
  const client = {
    repos: {
      repoGetContents: jest.fn(async (_o: string, _r: string, path: string) => {
        if (!(path in remote)) {
          throw Object.assign(new Error("not found"), { status: 404 });
        }
        return {
          data: {
            content: Buffer.from(remote[path]).toString("base64"),
            encoding: "base64",
            sha: `blob-${remote[path].length}`,
          },
        };
      }),
      repoChangeFiles: jest.fn(
        async (
          _o: string,
          _r: string,
          body: { files: Array<{ path: string; content: string }> },
        ) => {
          attempt += 1;
          beforeCommit?.(attempt);
          const landed = Object.fromEntries(
            body.files.map((f) => [
              f.path,
              Buffer.from(f.content, "base64").toString("utf8"),
            ]),
          );
          commits.push(landed);
          Object.assign(remote, landed);
        },
      ),
    },
  };
  return { client, commits };
}

const line = (n: number) =>
  `2024-01-${String(n).padStart(2, "0")} open Assets:A${n} USD`;
const lines = (...ns: number[]) => `${ns.map(line).join("\n")}\n`;
const replaceWith = (text: string) => new Map([["main.bean", () => text]]);

beforeEach(() => {
  for (const key of Object.keys(remote)) delete remote[key];
  countMock.mockClear();
  limitMock.mockReset();
});

describe("commitLedgerFiles and the directive limit", () => {
  it("refuses a commit that takes a free ledger past its limit, and commits nothing", async () => {
    remote["main.bean"] = lines(1, 2);
    limitMock.mockResolvedValue(2);
    const { client, commits } = repository();

    await expect(
      commitLedgerFiles(
        client as never,
        "alice",
        "books",
        replaceWith(lines(1, 2, 3, 4)),
        "Update entry",
        { directiveLimit: {} },
      ),
    ).rejects.toMatchObject({
      metadata: expect.objectContaining({
        code: "directive_limit_exceeded",
        details: { limit: 2, current: 4 },
      }),
    });
    expect(commits).toEqual([]);
  });

  it("commits a change within the limit", async () => {
    remote["main.bean"] = lines(1);
    limitMock.mockResolvedValue(2);
    const { client, commits } = repository();

    await commitLedgerFiles(
      client as never,
      "alice",
      "books",
      replaceWith(lines(1, 2)),
      "Update entry",
      { directiveLimit: {} },
    );

    expect(commits).toEqual([{ "main.bean": lines(1, 2) }]);
  });

  it("re-checks a retried commit against the content that retry would commit", async () => {
    remote["main.bean"] = lines(1);
    limitMock.mockResolvedValue(2);
    // A concurrent writer lands a directive between our read and our commit.
    const { client, commits } = repository((attempt) => {
      if (attempt === 1) {
        remote["main.bean"] = lines(1, 9);
        throw conflict;
      }
    });
    const append = new Map([
      ["main.bean", (current: string | null) => `${current ?? ""}${line(2)}\n`],
    ]);

    // First attempt: 1 → 2, within the limit. The retry would make it 3.
    await expect(
      commitLedgerFiles(
        client as never,
        "alice",
        "books",
        append,
        "Add entry",
        { directiveLimit: {} },
      ),
    ).rejects.toMatchObject({
      metadata: expect.objectContaining({ code: "directive_limit_exceeded" }),
    });
    expect(commits).toEqual([]);
    expect(remote["main.bean"]).toBe(lines(1, 9));
    // Both attempts were checked, against one tier lookup.
    expect(limitMock).toHaveBeenCalledTimes(1);
    expect(countMock).toHaveBeenCalledTimes(3);
  });

  it("lets a shrinking commit through on a ledger already over the limit", async () => {
    remote["main.bean"] = lines(1, 2, 3);
    limitMock.mockResolvedValue(1);
    const { client, commits } = repository();

    await commitLedgerFiles(
      client as never,
      "alice",
      "books",
      replaceWith(lines(1, 2)),
      "Delete entry",
      { directiveLimit: {} },
    );

    expect(commits).toEqual([{ "main.bean": lines(1, 2) }]);
  });

  it("does not count an exempt request", async () => {
    remote["main.bean"] = lines(1);
    limitMock.mockResolvedValue(0);
    const { client, commits } = repository();

    await commitLedgerFiles(
      client as never,
      "alice",
      "books",
      replaceWith(lines(1, 2, 3)),
      "Update entry",
      { directiveLimit: { exempt: true } },
    );

    expect(commits).toHaveLength(1);
    expect(limitMock).not.toHaveBeenCalled();
    expect(countMock).not.toHaveBeenCalled();
  });

  it("does not count a paid ledger", async () => {
    remote["main.bean"] = lines(1);
    limitMock.mockResolvedValue(-1);
    const { client, commits } = repository();

    await commitLedgerFiles(
      client as never,
      "alice",
      "books",
      replaceWith(lines(1, 2, 3)),
      "Update entry",
      { directiveLimit: {} },
    );

    expect(commits).toHaveLength(1);
    expect(countMock).not.toHaveBeenCalled();
  });
});
