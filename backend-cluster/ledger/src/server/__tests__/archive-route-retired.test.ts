import http from "node:http";
import { config } from "@/config";
import { clearMemoizedGiteaClients } from "@/features/gitea/service/gitea-client-factory";
import { buildApp } from "@/server/start-server";

/**
 * The archive download left this service in w0/m8: it read the whole archive
 * into memory with no deadline or size cap, and only forwarded backend-v2's
 * credential to Gitea. backend-v2 now streams Gitea's archive itself, so the
 * route must stay gone rather than come back as a second, buffering path.
 */
async function listen(server: http.Server): Promise<string> {
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  return `http://127.0.0.1:${(server.address() as { port: number }).port}`;
}

describe("the retired ledger archive route", () => {
  const giteaRequests: string[] = [];
  let giteaServer: http.Server;
  let ledgerServer: http.Server;
  let ledgerUrl: string;
  const originalGiteaUrl = config.gitea.baseUrl;

  beforeAll(async () => {
    giteaServer = http.createServer((request, response) => {
      giteaRequests.push(request.url!);
      response.setHeader("content-type", "application/zip");
      response.end("ZIPBYTES");
    });
    config.gitea.baseUrl = await listen(giteaServer);
    clearMemoizedGiteaClients();
    ledgerServer = http.createServer(buildApp().callback());
    ledgerUrl = await listen(ledgerServer);
  });

  afterAll(async () => {
    await Promise.all(
      [ledgerServer, giteaServer].map(
        (server) =>
          new Promise<void>((resolve) => server.close(() => resolve())),
      ),
    );
    config.gitea.baseUrl = originalGiteaUrl;
    clearMemoizedGiteaClients();
  });

  it.each(["main.zip", "main.tar.gz"])(
    "answers %s with 404 and never reaches Gitea",
    async (archive) => {
      const response = await fetch(
        `${ledgerUrl}/ledgers/alice/book/archive/${archive}`,
        {
          headers: {
            Authorization: `Basic ${Buffer.from("alice:fixture-only").toString("base64")}`,
          },
        },
      );
      expect(response.status).toBe(404);
      expect(giteaRequests).toEqual([]);
    },
  );
});
