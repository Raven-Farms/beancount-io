import http from "node:http";
import { buildApp } from "@/server/start-server";

/**
 * The ledger service serves no archive download (w0/m8): backend-v2 streams
 * Gitea's archive itself, and a route here would be a second, buffering path.
 */
describe("the ledger archive route", () => {
  let server: http.Server;
  let url: string;

  beforeAll(async () => {
    server = http.createServer(buildApp().callback());
    await new Promise<void>((resolve) =>
      server.listen(0, "127.0.0.1", resolve),
    );
    url = `http://127.0.0.1:${(server.address() as { port: number }).port}`;
  });

  afterAll(() => new Promise<void>((resolve) => server.close(() => resolve())));

  it("does not exist", async () => {
    const response = await fetch(`${url}/ledgers/alice/book/archive/main.zip`, {
      headers: {
        Authorization: `Basic ${Buffer.from("alice:fixture-only").toString("base64")}`,
      },
    });
    expect(response.status).toBe(404);
  });
});
