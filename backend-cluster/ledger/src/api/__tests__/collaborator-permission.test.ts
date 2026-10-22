import http from "node:http";
import Koa from "koa";
import Router from "@koa/router";
import bodyParser from "koa-bodyparser";
import { config } from "@/config";
import { setCollaboratorsHandler } from "@/api/collaborators";
import { restErrorMiddleware } from "@/server/error-middleware";
import { clearMemoizedGiteaClients } from "@/features/gitea/service/gitea-client-factory";

const AUTH = `Basic ${Buffer.from("alice:synthetic-password").toString("base64")}`;
const REPO = "/api/v1/repos/alice/books/collaborators/";

function user(login: string): Record<string, unknown> {
  return {
    id: 7,
    login,
    full_name: `Synthetic ${login}`,
    email: `${login}@example.invalid`,
    last_login: "2026-01-02T00:00:00Z",
  };
}

async function listen(server: http.Server): Promise<string> {
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  return `http://127.0.0.1:${(server.address() as { port: number }).port}`;
}

describe("collaborator permission lookup through the real handler and Gitea HTTP client", () => {
  const paths: string[] = [];
  // Logins the host treats as collaborators on alice/books.
  const collaborators = new Set<string>();
  let checkStatus: number | null = null;
  let ledgerServer: http.Server;
  let upstreamServer: http.Server;
  let ledgerUrl: string;
  const originalGiteaUrl = config.gitea.baseUrl;

  beforeAll(async () => {
    // The host answers the permission route for any account, as Gitea does.
    upstreamServer = http.createServer((request, response) => {
      const path = request.url!;
      paths.push(path);
      const send = (status: number, data?: unknown) => {
        response.writeHead(status, { "content-type": "application/json" });
        response.end(data === undefined ? "" : JSON.stringify(data));
      };
      if (request.method === "GET" && path.startsWith(REPO)) {
        const [login, operation] = path.slice(REPO.length).split("/");
        if (operation === "permission")
          return send(200, {
            permission: "read",
            role_name: "read",
            user: user(decodeURIComponent(login)),
          });
        if (!operation) {
          if (checkStatus !== null)
            return send(checkStatus, { message: "synthetic" });
          return collaborators.has(decodeURIComponent(login))
            ? send(204)
            : send(404, { message: "Not Found" });
        }
      }
      return send(500, { message: `Unexpected synthetic request: ${path}` });
    });
    config.gitea.baseUrl = await listen(upstreamServer);
    clearMemoizedGiteaClients();
    const app = new Koa();
    const router = new Router();
    setCollaboratorsHandler(router);
    app
      .use(restErrorMiddleware())
      .use(bodyParser())
      .use(router.routes())
      .use(router.allowedMethods());
    ledgerServer = http.createServer(app.callback());
    ledgerUrl = await listen(ledgerServer);
  });

  beforeEach(() => {
    paths.length = 0;
    collaborators.clear();
    collaborators.add("bob");
    checkStatus = null;
  });

  afterAll(async () => {
    await Promise.all(
      [ledgerServer, upstreamServer].map(
        (server) =>
          new Promise<void>((resolve) => server.close(() => resolve())),
      ),
    );
    config.gitea.baseUrl = originalGiteaUrl;
    clearMemoizedGiteaClients();
  });

  const lookup = async (collaborator: string) => {
    const response = await fetch(
      `${ledgerUrl}/collaborators/alice/books/${encodeURIComponent(collaborator)}`,
      { headers: { authorization: AUTH }, signal: AbortSignal.timeout(5000) },
    );
    const body = (await response.json()) as {
      success: boolean;
      error?: string;
      data?: { permission: string; user: { login: string } };
    };
    return { status: response.status, body };
  };
  const permissionCalls = () => paths.filter((p) => p.endsWith("/permission"));

  it("answers for a collaborator", async () => {
    const { status, body } = await lookup("bob");
    expect(status).toBe(200);
    expect(body.data).toMatchObject({
      permission: "read",
      user: { login: "bob" },
    });
  });

  it("answers for the owner, whatever the case, without a membership check", async () => {
    const { status, body } = await lookup("Alice");
    expect(status).toBe(200);
    expect(body.data?.user.login).toBe("Alice");
    expect(paths).toEqual([`${REPO}Alice/permission`]);
  });

  it("refuses a user who is not a collaborator without fetching their profile", async () => {
    const { status, body } = await lookup("carol");
    expect(status).toBe(404);
    expect(body.success).toBe(false);
    expect(body.error).toBe("Collaborator 'carol' not found");
    expect(JSON.stringify(body)).not.toContain("example.invalid");
    expect(permissionCalls()).toEqual([]);
  });

  it("encodes the name so it cannot address another host route", async () => {
    const { status } = await lookup("../../../admin");
    expect(status).toBe(404);
    expect(paths).toEqual([`${REPO}..%2F..%2F..%2Fadmin`]);
  });

  it("passes a host failure other than 404 through instead of refusing", async () => {
    checkStatus = 503;
    const { status } = await lookup("bob");
    expect(status).not.toBe(200);
    expect(status).not.toBe(404);
    expect(permissionCalls()).toEqual([]);
  });
});
