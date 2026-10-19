import "reflect-metadata";
jest.mock("@ai-sdk/harness/agent", () => ({ HarnessAgent: class {} }));
jest.mock("@ai-sdk/harness-acp", () => ({ createACP: () => ({}) }));
import http from "node:http";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { LedgerArchiveService } from "@/features/ledger/service/ledger-archive-service";
import { AuthorizationService } from "@/server/api/authorization";
import { assembleMcpRegistry } from "@/server/api/composition-root";
import { readOnlyToken } from "@/server/rest/__tests__/v1-test-server";
import type { AppConfig } from "@/config/config";
import type { McpRequestContext } from "../mcp-context";
import { MCP_ARCHIVE_BLOB_MAX_BYTES } from "../mcp-resources";

/**
 * The MCP archive blob's size cap (w0/m8). A resource read is one JSON-RPC
 * message, so the archive is held whole where REST streams it; past the cap
 * the read is refused and points at the streaming download URL. The origin is
 * a real HTTP server standing in for Gitea, so "stops reading" is observed as
 * the upstream socket closing rather than assumed.
 */
const URI = "beancount://alice/main/archive/main.zip";
const CHUNK = 256 * 1024;

type Serve = (res: http.ServerResponse) => void;

async function fixture(serve: Serve) {
  const upstream: { req?: http.IncomingMessage; closed: Promise<void> } = {
    closed: Promise.resolve(),
  };
  const origin = http.createServer((req, res) => {
    upstream.req = req;
    upstream.closed = new Promise((resolve) =>
      req.socket.once("close", () => resolve()),
    );
    res.setHeader("Content-Type", "application/zip");
    res.setHeader("Content-Disposition", 'attachment; filename="main.zip"');
    serve(res);
  });
  await new Promise<void>((resolve) => origin.listen(0, "127.0.0.1", resolve));
  const { port } = origin.address() as { port: number };
  const config = {
    api: { scopeEnforcement: "enforce" },
    gitea: { internalBaseUrl: `http://127.0.0.1:${port}` },
  } as AppConfig;
  const authorization = new AuthorizationService(
    { check: jest.fn().mockResolvedValue(true) },
    jest.fn(),
  );
  const service = new LedgerArchiveService(
    {
      user: {
        getById: async () => ({
          ledger_username: "alice",
          ledger_password: "fixture-only",
        }),
      },
    } as never,
    {} as never,
    config,
    authorization,
  );
  const server = assembleMcpRegistry(
    {
      identity: readOnlyToken,
      ledgerArchiveService: service,
    } as unknown as McpRequestContext,
    config,
  );
  const client = new Client({ name: "archive-blob-cap", version: "1" });
  const [a, b] = InMemoryTransport.createLinkedPair();
  await Promise.all([client.connect(a), server.connect(b)]);
  return {
    upstream,
    read: () => client.readResource({ uri: URI }),
    close: async () => {
      await client.close();
      await server.close();
      origin.closeAllConnections();
      await new Promise<void>((resolve) => origin.close(() => resolve()));
    },
  };
}

/** Writes `total` bytes in chunks, honouring backpressure; `Infinity` never ends. */
function stream(res: http.ServerResponse, total: number) {
  let sent = 0;
  const pump = (): void => {
    while (sent < total && !res.destroyed) {
      const size = Math.min(CHUNK, total - sent);
      sent += size;
      if (!res.write(Buffer.alloc(size, 7))) {
        res.once("drain", pump);
        return;
      }
    }
    if (sent >= total) res.end();
  };
  pump();
}

const refusal = {
  code: -32003,
  data: {
    code: "OPERATION_NOT_ALLOWED",
    message: expect.stringContaining("8 MiB"),
    hint: expect.stringContaining(
      "beancount://alice/main/archive-download-url",
    ),
  },
};

describe("the MCP archive blob cap", () => {
  it.each([
    ["with", true],
    ["without", false],
  ])(
    "returns an archive of exactly the cap %s Content-Length",
    async (_label, declared) => {
      const f = await fixture((res) => {
        if (declared)
          res.setHeader("Content-Length", MCP_ARCHIVE_BLOB_MAX_BYTES);
        stream(res, MCP_ARCHIVE_BLOB_MAX_BYTES);
      });
      try {
        const content = (await f.read()).contents[0];
        if (!("blob" in content)) throw new Error("Expected archive blob");
        const bytes = Buffer.from(content.blob, "base64");
        expect(bytes.length).toBe(MCP_ARCHIVE_BLOB_MAX_BYTES);
        expect(bytes.every((byte) => byte === 7)).toBe(true);
        expect(content.mimeType).toBe("application/zip");
      } finally {
        await f.close();
      }
    },
  );

  it("refuses by Content-Length before reading the body", async () => {
    // One chunk and then nothing: a reader that waited for the body would
    // never finish, so only the up-front check can answer.
    const f = await fixture((res) => {
      res.setHeader("Content-Length", MCP_ARCHIVE_BLOB_MAX_BYTES + 1);
      res.write(Buffer.alloc(CHUNK, 7));
    });
    try {
      await expect(f.read()).rejects.toMatchObject(refusal);
      await f.upstream.closed;
    } finally {
      await f.close();
    }
  });

  it("refuses an undeclared archive once it passes the cap and stops the upstream", async () => {
    // An endless body: the read can only end by giving up on it.
    const f = await fixture((res) => stream(res, Infinity));
    try {
      await expect(f.read()).rejects.toMatchObject(refusal);
      await f.upstream.closed;
    } finally {
      await f.close();
    }
  });
});
