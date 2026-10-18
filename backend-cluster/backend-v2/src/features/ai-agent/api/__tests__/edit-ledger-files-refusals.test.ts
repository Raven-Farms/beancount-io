import "reflect-metadata";
jest.mock("@ai-sdk/harness/agent", () => ({ HarnessAgent: class {} }));
jest.mock("@ai-sdk/harness-acp", () => ({ createACP: () => ({}) }));
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { LedgerRepoService } from "@/features/ledger/service/ledger-repo-service";
import { AuthorizationService } from "@/server/api/authorization";
import { assembleMcpRegistry } from "@/server/api/composition-root";
import type { AppConfig } from "@/config/config";
import type { Identity } from "@/server/api/identity";
import type { McpRequestContext } from "../mcp-context";

/**
 * w5/035. The file-edit tools promise that a dry run gives "the same refusal as
 * the commit", and describes `create` as a new file. The preview nevertheless
 * approved a `create` over a file that already exists. Driven through the real
 * registry and repo service, with only the ledger client faked.
 */
const config = { api: { scopeEnforcement: "enforce" } } as AppConfig;
const identity: Identity = {
  userId: "usr_alice",
  method: "oauth",
  scopes: new Set(["ledger.read", "ledger.write"]),
  tokenId: "tok_edit_preview",
};

async function fixture() {
  const existing = new Set(["main.bean", "accounts.bean"]);
  const getLedgerFilesContent = jest.fn(
    async (_owner: string, _name: string, { files }: { files: string[] }) => ({
      data: {
        success: true,
        data: files
          .filter((path) => existing.has(path))
          .map((path) => ({
            path,
            name: path,
            type: "file",
            sha: "s1",
            content: '2026-01-05 * "Cafe"\n2026-02-05 * "Cafe"\n',
          })),
      },
    }),
  );
  const changeLedgerFiles = jest.fn();
  const authorization = new AuthorizationService(
    { check: jest.fn().mockResolvedValue(true) },
    jest.fn(),
  );
  const services = {
    ledgerRepo: new LedgerRepoService(
      {
        getPublicApiClient: async () => ({
          ledgers: { getLedgerFilesContent, changeLedgerFiles },
        }),
      } as never,
      authorization,
    ),
  };
  const server = assembleMcpRegistry(
    { identity, services } as unknown as McpRequestContext,
    config,
  );
  const client = new Client({ name: "edit-preview", version: "1" });
  const [a, b] = InMemoryTransport.createLinkedPair();
  await Promise.all([client.connect(a), server.connect(b)]);
  return {
    changeLedgerFiles,
    getLedgerFilesContent,
    preview: (path: string) =>
      client.callTool({
        name: "createLedgerFiles",
        arguments: {
          ledger: "alice/main",
          description: "add a file",
          dry_run: true,
          files: [{ path, content: "; new\n" }],
        },
      }),
    client,
    update: (old_string: string) =>
      client.callTool({
        name: "updateLedgerFiles",
        arguments: {
          ledger: "alice/main",
          description: "rename a payee",
          dry_run: true,
          files: [{ path: "main.bean", old_string, new_string: "Bakery" }],
        },
      }),
    close: async () => {
      await client.close();
      await server.close();
    },
  };
}

describe("previewing a create over an existing file", () => {
  it("is refused as a conflict that names the file and the way to overwrite it", async () => {
    const f = await fixture();
    try {
      const result = await f.preview("main.bean");
      expect(result.isError).toBe(true);
      const { error } = result.structuredContent as {
        error: { code: string; message: string; hint: string };
      };
      expect(error.code).toBe("CONFLICT");
      expect(error.message).toContain("main.bean already exists");
      expect(error.hint).toContain("replace");
      // The category's fallback hint is about entry editing; it must not win.
      expect(error.hint).not.toContain("getEntryContext");
      expect(f.changeLedgerFiles).not.toHaveBeenCalled();
    } finally {
      await f.close();
    }
  });
});

/**
 * w1/m38. Splitting `editLedgerFiles` into one tool per kind of change kept
 * the batch: every file a call names lands in the same commit, so a partial
 * write cannot leave the ledger half-restructured.
 */
describe("one call to a file tool", () => {
  const decode = (content?: string) =>
    content === undefined
      ? undefined
      : Buffer.from(content, "base64").toString();

  it.each([
    [
      "createLedgerFiles",
      [
        { path: "a.bean", content: "; a\n" },
        { path: "b.bean", content: "; b\n" },
      ],
      [
        { operation: "create", path: "a.bean", text: "; a\n" },
        { operation: "create", path: "b.bean", text: "; b\n" },
      ],
    ],
    [
      "updateLedgerFiles",
      [
        {
          path: "main.bean",
          old_string: '01-05 * "Cafe"',
          new_string: '01-05 * "Bakery"',
        },
        { path: "accounts.bean", content: "; replaced\n" },
      ],
      [
        {
          operation: "update",
          path: "main.bean",
          text: '2026-01-05 * "Bakery"\n2026-02-05 * "Cafe"\n',
        },
        { operation: "update", path: "accounts.bean", text: "; replaced\n" },
      ],
    ],
    [
      "deleteLedgerFiles",
      [{ path: "main.bean" }, { path: "accounts.bean" }],
      [
        { operation: "delete", path: "main.bean", text: undefined },
        { operation: "delete", path: "accounts.bean", text: undefined },
      ],
    ],
  ])(
    "%s commits every file it names in one commit",
    async (name, files, expected) => {
      const f = await fixture();
      f.changeLedgerFiles.mockResolvedValue({
        data: { success: true, data: {} },
      });
      try {
        const result = await f.client.callTool({
          name,
          arguments: {
            ledger: "alice/main",
            description: "restructure",
            files,
          },
        });
        expect(result.isError).toBeFalsy();
        expect(f.changeLedgerFiles).toHaveBeenCalledTimes(1);
        const [, , body] = f.changeLedgerFiles.mock.calls[0] as [
          string,
          string,
          {
            message: string;
            files: { operation: string; path: string; content?: string }[];
          },
        ];
        expect(body.message).toBe("restructure");
        expect(
          body.files.map(({ operation, path, content }) => ({
            operation,
            path,
            text: decode(content),
          })),
        ).toEqual(expected);
      } finally {
        await f.close();
      }
    },
  );
});

/** w5/036: an ambiguous `old_string` is the caller's to fix, in production too. */
describe("an old_string that matches more than once", () => {
  it("is refused as bad input with the count and a way forward", async () => {
    const f = await fixture();
    try {
      const result = await f.update("Cafe");
      expect(result.isError).toBe(true);
      const { error } = result.structuredContent as {
        error: { code: string; message: string; hint: string };
      };
      expect(error.code).toBe("BAD_USER_INPUT");
      expect(error.message).toContain("matches 2 times");
      expect(error.hint).not.toMatch(/retry/i);
      expect(f.changeLedgerFiles).not.toHaveBeenCalled();
    } finally {
      await f.close();
    }
  });
});

/**
 * w5/039. A plain Zod object strips keys it does not name, so a misspelt
 * `dry_run` was dropped, the default of false applied, and the call committed
 * what the caller meant to preview. The `tools/call` boundary now refuses an
 * argument the tool does not declare, on every tool.
 */
describe("an argument the tool does not declare", () => {
  it.each(["dryrun", "dryRun", "bogus"])(
    "refuses %s on createLedgerFiles instead of committing",
    async (typo) => {
      const f = await fixture();
      try {
        const result = await f.client.callTool({
          name: "createLedgerFiles",
          arguments: {
            ledger: "alice/main",
            description: "add a file",
            [typo]: true,
            files: [{ path: "new.bean", content: "x\n" }],
          },
        });
        expect(result.isError).toBe(true);
        const { error } = result.structuredContent as {
          error: { code: string; message: string };
        };
        expect(error.code).toBe("BAD_USER_INPUT");
        expect(error.message).toContain(typo);
        expect(f.changeLedgerFiles).not.toHaveBeenCalled();
      } finally {
        await f.close();
      }
    },
  );

  it.each([
    ["readLedgerFiles", { files: [{ path: "main.bean" }] }],
    ["listLedgerFiles", {}],
    ["refreshBankConnection", { item_id: "pitm_1" }],
    ["syncBankTransactions", { item_id: "pitm_1" }],
  ])(
    "refuses an unknown argument on %s before the tool runs",
    async (name, args) => {
      const f = await fixture();
      try {
        const result = await f.client.callTool({
          name,
          arguments: { ledger: "alice/main", ...args, bogus: 1 },
        });
        expect(result.isError).toBe(true);
        expect(result.structuredContent).toMatchObject({
          error: {
            code: "BAD_USER_INPUT",
            message: expect.stringContaining("bogus"),
          },
        });
        expect(f.getLedgerFilesContent).not.toHaveBeenCalled();
      } finally {
        await f.close();
      }
    },
  );
});
