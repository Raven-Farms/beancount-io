import { LedgerArchiveService } from "@/features/ledger/service/ledger-archive-service";
import {
  startArchiveOrigin,
  type ArchiveOrigin,
} from "@/features/ledger/service/__tests__/archive-origin";
import http from "node:http";
import Koa from "koa";
import Router from "@koa/router";
import type { AppConfig } from "@/config/config";
import type { AppLayers } from "@/foundation/composition";
import { restErrorMiddleware } from "@/server/rest/error-middleware";
import { registerDownloadArchiveRoute } from "../download-archive-handler";
import { NotFoundError, UnauthenticatedError } from "@/shared/errors";

/**
 * The legacy archive download over HTTP.
 *
 * The one property these tests exist to hold: a credential in the query string
 * is not a credential on this route. It once was — `?token=<JWT>` carried the
 * caller's whole session in every URL — and the regression these tests pin is
 * that a private ledger refuses such a request before any upstream fetch.
 */
const mockGetLedger = jest.fn();

const layers = {
  database: {
    db: undefined,
    models: { user: { getById: jest.fn() } },
  },
  clients: {
    favaClientFactory: {
      getAdminClient: () => ({ ledgers: { getLedger: mockGetLedger } }),
    },
  },
  services: {
    authorization: {
      authorizeOrThrow: jest.fn(async () => {
        const response = await mockGetLedger();
        if (!response.data.success) throw new NotFoundError("Ledger");
        if (response.data.data.private) {
          throw new UnauthenticatedError("Authentication required");
        }
        return { allowed: true };
      }),
    },
  },
} as unknown as AppLayers;

let baseUrl: string;
let server: http.Server;
let origin: ArchiveOrigin;

beforeAll(async () => {
  origin = await startArchiveOrigin();
  const config = {
    gitea: { internalBaseUrl: origin.url },
  } as unknown as AppConfig;
  layers.services.ledgerArchive = new LedgerArchiveService(
    layers.database.models,
    layers.database.db,
    config,
    layers.services.authorization,
  );
  const router = new Router();
  router.use(restErrorMiddleware());
  registerDownloadArchiveRoute(router, layers, config);
  const app = new Koa();
  app.silent = true;
  app.use(router.routes()).use(router.allowedMethods());
  server = http.createServer(app.callback());
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  if (typeof address !== "object" || !address) throw new Error("no port");
  baseUrl = `http://127.0.0.1:${address.port}`;
});

afterAll(async () => {
  server.close();
  await origin.close();
});

beforeEach(() => {
  origin.reset();
});

describe("legacy archive download", () => {
  it("refuses a private ledger when the only credential is a JWT in the query string", async () => {
    mockGetLedger.mockResolvedValue({
      data: { success: true, data: { private: true } },
    });

    const response = await fetch(
      `${baseUrl}/api-gateway/ledgers/alice%2Fpersonal/archive/main.zip?token=a.jwt.value`,
    );

    expect(response.status).toBe(401);
    expect(origin.requests).toHaveLength(0);
  });

  it("streams a public ledger's archive to an anonymous caller with no credential", async () => {
    mockGetLedger.mockResolvedValue({
      data: { success: true, data: { private: false } },
    });

    const response = await fetch(
      `${baseUrl}/api-gateway/ledgers/alice%2Fpublic/archive/main.zip`,
    );

    expect(response.status).toBe(200);
    expect(await response.text()).toBe("ZIPBYTES");
    expect(origin.requests.map((r) => r.url)).toEqual([
      "/api/v1/repos/alice/public/archive/main.zip",
    ]);
    expect(origin.requests[0].headers).not.toHaveProperty("authorization");
  });

  it("reports an unknown ledger as 404 without an upstream request", async () => {
    mockGetLedger.mockResolvedValue({ data: { success: false } });

    const response = await fetch(
      `${baseUrl}/api-gateway/ledgers/nobody%2Fmain/archive/main.zip`,
    );

    expect(response.status).toBe(404);
    expect(origin.requests).toHaveLength(0);
  });

  it("still rejects a traversal archive name before anything downstream", async () => {
    const response = await fetch(
      `${baseUrl}/api-gateway/ledgers/alice%2Fpublic/archive/..%2F..%2Fjournal`,
    );

    expect(response.status).toBe(400);
    expect(origin.requests).toHaveLength(0);
  });
});
