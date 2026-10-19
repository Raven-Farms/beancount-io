import http from "node:http";
import type { IAuthorizationService } from "@/server/api/authorization";
import { LedgerArchiveService } from "../ledger-archive-service";

/**
 * A real HTTP server standing in for Gitea's archive API, so the request
 * backend-v2 sends and the upstream socket's lifetime are observed rather than
 * mocked. Shared by the archive service, REST, and MCP tests.
 */
type Handler = (req: http.IncomingMessage, res: http.ServerResponse) => void;

const serveZip: Handler = (_req, res) => {
  res.setHeader("Content-Type", "application/zip");
  res.setHeader("Content-Disposition", 'attachment; filename="main.zip"');
  res.end("ZIPBYTES");
};

export interface ArchiveOrigin {
  url: string;
  /** Every request the origin received, in order. */
  requests: http.IncomingMessage[];
  /** Replace how the origin answers; the default sends `ZIPBYTES` as main.zip. */
  serve(handler: Handler): void;
  /** Forget recorded requests and go back to the default answer. */
  reset(): void;
  close(): Promise<void>;
}

export async function startArchiveOrigin(): Promise<ArchiveOrigin> {
  const requests: http.IncomingMessage[] = [];
  let handler = serveZip;
  const server = http.createServer((req, res) => {
    requests.push(req);
    handler(req, res);
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as { port: number };
  return {
    url: `http://127.0.0.1:${port}`,
    requests,
    serve: (next) => {
      handler = next;
    },
    reset: () => {
      requests.length = 0;
      handler = serveZip;
    },
    close: () => {
      server.closeAllConnections();
      return new Promise<void>((resolve) => server.close(() => resolve()));
    },
  };
}

/** Whether the upstream socket of `req` closes within `ms`. */
export function closed(req: http.IncomingMessage, ms = 2_000) {
  return new Promise<"closed" | "still open">((resolve) => {
    const timer = setTimeout(() => resolve("still open"), ms);
    req.socket.once("close", () => {
      clearTimeout(timer);
      resolve("closed");
    });
  });
}

/** The archive service against `origin`, signed in as alice. */
export function archiveServiceFor(
  origin: ArchiveOrigin,
  authorization: IAuthorizationService = {
    authorizeOrThrow: jest.fn().mockResolvedValue({ allowed: true }),
  } as never,
) {
  return new LedgerArchiveService(
    {
      user: {
        getById: async () => ({
          ledger_username: "alice",
          ledger_password: "fixture-only",
        }),
      },
    } as never,
    {} as never,
    { gitea: { internalBaseUrl: origin.url } } as never,
    authorization,
  );
}
