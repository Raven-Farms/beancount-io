import http from "node:http";
import type { Readable } from "node:stream";
import type { Identity } from "@/server/api/identity";
import { NotFoundError, ServiceUnavailableError } from "@/shared/errors";
import {
  ARCHIVE_HEADERS_TIMEOUT_MS,
  LedgerArchiveService,
} from "../ledger-archive-service";

/**
 * The archive download against a real HTTP origin standing in for Gitea, so
 * the request backend-v2 sends and the socket's lifetime are observed rather
 * than assumed (w0/m8). The ledger service is no longer on this path.
 */
const alice = { userId: "usr_alice" } as Identity;

type Handler = (req: http.IncomingMessage, res: http.ServerResponse) => void;

async function gitea(handler: Handler) {
  const requests: http.IncomingMessage[] = [];
  const server = http.createServer((req, res) => {
    requests.push(req);
    handler(req, res);
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as { port: number };
  const authorizeOrThrow = jest.fn().mockResolvedValue({ allowed: true });
  const service = new LedgerArchiveService(
    {
      user: {
        getById: jest.fn(async () => ({
          ledger_username: "alice",
          ledger_password: "fixture-only",
        })),
      },
    } as never,
    {} as never,
    { gitea: { internalBaseUrl: `http://127.0.0.1:${port}` } } as never,
    { authorizeOrThrow } as never,
  );
  return {
    service,
    requests,
    close: () => {
      server.closeAllConnections();
      return new Promise<void>((resolve) => server.close(() => resolve()));
    },
  };
}

function closed(req: http.IncomingMessage, ms = 2_000) {
  return new Promise<"closed" | "still open">((resolve) => {
    const timer = setTimeout(() => resolve("still open"), ms);
    req.socket.once("close", () => {
      clearTimeout(timer);
      resolve("closed");
    });
  });
}

describe("LedgerArchiveService", () => {
  afterEach(() => jest.restoreAllMocks());

  it("reads Gitea's archive API with the caller's Gitea credentials", async () => {
    const g = await gitea((_req, res) => {
      res.setHeader("Content-Type", "application/zip");
      res.end("ZIPBYTES");
    });
    try {
      const response = await g.service.download({
        identity: alice,
        ledgerId: "alice/main",
        archive: "main.zip",
      });
      expect(await response.text()).toBe("ZIPBYTES");
      expect(g.requests.map((r) => r.url)).toEqual([
        "/api/v1/repos/alice/main/archive/main.zip",
      ]);
      expect(g.requests[0].headers.authorization).toBe(
        `Basic ${Buffer.from("alice:fixture-only").toString("base64")}`,
      );
    } finally {
      await g.close();
    }
  });

  it("sends no credential at all for an anonymous public read", async () => {
    const g = await gitea((_req, res) => res.end("ZIPBYTES"));
    try {
      const response = await g.service.download({
        ledgerId: "alice/public",
        archive: "main.tar.gz",
      });
      await response.text();
      expect(g.requests[0].url).toBe(
        "/api/v1/repos/alice/public/archive/main.tar.gz",
      );
      expect(g.requests[0].headers).not.toHaveProperty("authorization");
    } finally {
      await g.close();
    }
  });

  it.each([
    [404, NotFoundError],
    [401, ServiceUnavailableError],
    [500, ServiceUnavailableError],
  ])("maps Gitea %s to %p", async (status, error) => {
    const g = await gitea((_req, res) => {
      res.statusCode = status;
      res.end("upstream failure");
    });
    try {
      await expect(
        g.service.download({
          identity: alice,
          ledgerId: "alice/main",
          archive: "main.zip",
        }),
      ).rejects.toBeInstanceOf(error);
    } finally {
      await g.close();
    }
  });

  it("fails as unavailable when Gitea sends no headers before the deadline", async () => {
    const timers = jest.spyOn(global, "setTimeout");
    const g = await gitea(() => {
      // Never answers.
    });
    try {
      const download = g.service.download({
        identity: alice,
        ledgerId: "alice/main",
        archive: "main.zip",
      });
      while (g.requests.length === 0)
        await new Promise((resolve) => setImmediate(resolve));
      const deadline = timers.mock.calls.find(
        ([, ms]) => ms === ARCHIVE_HEADERS_TIMEOUT_MS,
      );
      expect(deadline).toBeDefined();
      const upstream = closed(g.requests[0]);
      (deadline![0] as () => void)();
      await expect(download).rejects.toBeInstanceOf(ServiceUnavailableError);
      expect(await upstream).toBe("closed");
    } finally {
      await g.close();
    }
  });

  it("clears the deadline once headers arrive, however long the body takes", async () => {
    const set = jest.spyOn(global, "setTimeout");
    const clear = jest.spyOn(global, "clearTimeout");
    const g = await gitea((_req, res) => res.end("ZIPBYTES"));
    try {
      const response = await g.service.download({
        identity: alice,
        ledgerId: "alice/main",
        archive: "main.zip",
      });
      const index = set.mock.calls.findIndex(
        ([, ms]) => ms === ARCHIVE_HEADERS_TIMEOUT_MS,
      );
      expect(clear).toHaveBeenCalledWith(set.mock.results[index].value);
      expect(await response.text()).toBe("ZIPBYTES");
    } finally {
      await g.close();
    }
  });

  it("aborts the Gitea request when the body is destroyed mid-download", async () => {
    const g = await gitea((_req, res) => {
      // A large archive: one chunk now, the rest never — only the caller ends it.
      res.setHeader("Content-Type", "application/zip");
      res.write(Buffer.alloc(64 * 1024));
    });
    try {
      const response = await g.service.download({
        identity: alice,
        ledgerId: "alice/main",
        archive: "main.zip",
      });
      const body = response.body as Readable;
      await new Promise((resolve) => body.once("data", resolve));
      const upstream = closed(g.requests[0]);
      body.destroy();
      expect(await upstream).toBe("closed");
    } finally {
      await g.close();
    }
  });
});
