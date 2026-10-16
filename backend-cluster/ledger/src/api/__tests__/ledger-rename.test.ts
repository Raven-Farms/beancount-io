import http from "node:http";
import Koa from "koa";
import Router from "@koa/router";
import bodyParser from "koa-bodyparser";
import { config } from "@/config";
import { setLedgersHandler } from "@/api/ledgers";
import { restErrorMiddleware } from "@/server/error-middleware";
import { clearMemoizedGiteaClients } from "@/features/gitea/service/gitea-client-factory";

const AUTH = `Basic ${Buffer.from("alice:synthetic-password").toString("base64")}`;
const BASE = "/api/v1/repos/alice/";
const CURRENT = "books-temp";
const TARGET = "books";
const FILE = 'option "title" "Synthetic books"\n';

type Call = {
  method: string;
  path: string;
  body: Record<string, unknown>;
  authorization?: string;
};
type Failure = { status: number; message: string };

function repository(name: string, id: unknown = 71): Record<string, unknown> {
  return {
    id,
    name,
    full_name: `alice/${name}`,
    private: true,
    empty: false,
    size: 10,
    description: "Synthetic books",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
    permissions: { admin: true, pull: true, push: true },
  };
}

async function listen(server: http.Server): Promise<string> {
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  return `http://127.0.0.1:${(server.address() as { port: number }).port}`;
}

describe("ledger rename collision identity through the real handler and Gitea HTTP client", () => {
  const calls: Call[] = [];
  const repos = new Map<string, unknown>();
  const redirects = new Map<string, string>();
  const failures = new Map<string, Failure>();
  const files = new Map<string, string>();
  let ledgerServer: http.Server;
  let upstreamServer: http.Server;
  let ledgerUrl: string;
  const originalGiteaUrl = config.gitea.baseUrl;

  beforeAll(async () => {
    // Only the external Gitea server is controlled. Routing, auth forwarding,
    // generated client/redirects, validation, handler and error mapping are real.
    upstreamServer = http.createServer(async (request, response) => {
      const chunks: Buffer[] = [];
      for await (const chunk of request) chunks.push(Buffer.from(chunk));
      const text = Buffer.concat(chunks).toString("utf8");
      const body = text ? (JSON.parse(text) as Record<string, unknown>) : {};
      const method = request.method!;
      const path = request.url!;
      calls.push({
        method,
        path,
        body,
        authorization: request.headers.authorization,
      });
      const send = (status: number, data: unknown) => {
        response.writeHead(status, { "content-type": "application/json" });
        response.end(JSON.stringify(data));
      };
      const failure = failures.get(`${method} ${path}`);
      if (failure) return send(failure.status, { message: failure.message });
      if (method === "POST" && path === "/api/v1/user/repos") {
        const created = repository(String(body.name));
        repos.set(String(body.name), created);
        return send(201, created);
      }
      if (path.startsWith(BASE)) {
        const suffix = path.slice(BASE.length);
        const [name, operation] = suffix.split("/");
        if (method === "GET" && !operation) {
          const redirect = redirects.get(name);
          if (redirect) {
            response.writeHead(307, { location: `${BASE}${redirect}` });
            return response.end();
          }
          return repos.has(name)
            ? send(200, repos.get(name))
            : send(404, { message: "Repository missing" });
        }
        if (method === "PATCH" && !operation) {
          const original = repos.get(name);
          if (!original || typeof original !== "object")
            return send(404, { message: "Repository missing" });
          const renamed = {
            ...original,
            ...body,
            full_name: `alice/${body.name ?? name}`,
          };
          repos.delete(name);
          repos.set(String(body.name ?? name), renamed);
          return send(200, renamed);
        }
        // Existing policies avoid unrelated policy writes in the create control.
        if (method === "GET" && operation === "branch_protections")
          return send(200, [
            { rule_name: "main", enable_push: true, priority: 1 },
            { rule_name: "*", enable_push: false, priority: 2 },
          ]);
        if (method === "GET" && operation === "tag_protections")
          return send(200, [
            { id: 9, name_pattern: "*", whitelist_usernames: [] },
          ]);
        if (method === "POST" && operation === "contents") {
          for (const file of body.files as Array<{
            path: string;
            content: string;
          }>) {
            files.set(
              file.path,
              Buffer.from(file.content, "base64").toString("utf8"),
            );
          }
          return send(201, {});
        }
      }
      return send(500, {
        message: `Unexpected synthetic request: ${method} ${path}`,
      });
    });
    config.gitea.baseUrl = await listen(upstreamServer);
    clearMemoizedGiteaClients();
    const app = new Koa();
    const router = new Router();
    setLedgersHandler(router);
    app
      .use(restErrorMiddleware())
      .use(bodyParser())
      .use(router.routes())
      .use(router.allowedMethods());
    ledgerServer = http.createServer(app.callback());
    ledgerUrl = await listen(ledgerServer);
  });

  beforeEach(() => {
    calls.length = 0;
    repos.clear();
    redirects.clear();
    failures.clear();
    files.clear();
    repos.set(CURRENT, repository(CURRENT));
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

  const request = async (
    body: Record<string, unknown>,
    method = "PUT",
    authorization: string | null = AUTH,
  ) => {
    const response = await fetch(
      `${ledgerUrl}/ledgers${method === "PUT" ? `/alice/${CURRENT}` : ""}`,
      {
        method,
        headers: {
          "content-type": "application/json",
          ...(authorization ? { authorization } : {}),
        },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(5000),
      },
    );
    return { status: response.status, body: await response.json() };
  };
  const mutations = () => calls.filter((call) => call.method !== "GET");
  const conflict = () => ({
    success: false,
    error: `A ledger with the name '${TARGET}' already exists. Please choose a different name.`,
    code: null,
    details: null,
  });

  it.each([71, Number.MAX_SAFE_INTEGER])(
    "renames back through an actual old-name redirect to repository %s",
    async (id) => {
      repos.set(CURRENT, repository(CURRENT, id));
      redirects.set(TARGET, CURRENT);
      const result = await request({ name: "Books" });
      expect(result).toEqual({
        status: 200,
        body: {
          success: true,
          data: { ...repository(TARGET, id), description: "Synthetic books" },
        },
      });
      expect(repos.get(TARGET)).toEqual(repository(TARGET, id));
      expect(mutations()).toEqual([
        {
          method: "PATCH",
          path: `${BASE}${CURRENT}`,
          body: { name: TARGET },
          authorization: AUTH,
        },
      ]);
      expect(
        calls.filter((call) => call.method === "GET").map((call) => call.path),
      ).toEqual([`${BASE}${TARGET}`, `${BASE}${CURRENT}`, `${BASE}${CURRENT}`]);
      expect(calls.every((call) => call.authorization === AUTH)).toBe(true);
      expect(files.size).toBe(0);
    },
  );

  it("rejects another repository even when its names and metadata look identical", async () => {
    repos.set(TARGET, repository(CURRENT, 72));
    expect(await request({ name: TARGET })).toEqual({
      status: 400,
      body: conflict(),
    });
    expect(mutations()).toEqual([]);
    expect(repos.get(CURRENT)).toEqual(repository(CURRENT));
  });

  const invalidIds = [
    undefined,
    null,
    0,
    -1,
    1.5,
    Number.MAX_SAFE_INTEGER + 1,
    "71",
  ];
  it.each(invalidIds)(
    "rejects an occupied target with invalid identity %s even if the source matches it",
    async (id) => {
      const invalid = { ...repository(CURRENT), id };
      repos.set(CURRENT, invalid);
      repos.set(TARGET, invalid);
      expect(await request({ name: TARGET })).toEqual({
        status: 400,
        body: conflict(),
      });
      expect(mutations()).toEqual([]);
    },
  );
  it.each(invalidIds)(
    "rejects invalid source identity %s beside a valid target",
    async (id) => {
      repos.set(CURRENT, { ...repository(CURRENT), id });
      repos.set(TARGET, repository(TARGET));
      expect(await request({ name: TARGET })).toEqual({
        status: 400,
        body: conflict(),
      });
      expect(mutations()).toEqual([]);
    },
  );

  it.each([null, false, 0, ""])(
    "treats successful target data %j as occupied",
    async (data) => {
      repos.set(TARGET, data);
      expect(await request({ name: TARGET })).toEqual({
        status: 400,
        body: conflict(),
      });
      expect(mutations()).toEqual([]);
    },
  );

  it("allows a genuinely unused target without an extra source read", async () => {
    const result = await request({ name: TARGET });
    expect(result.status).toBe(200);
    expect(result.body).toMatchObject({
      success: true,
      data: { id: 71, name: TARGET, private: true },
    });
    expect(calls.map((call) => `${call.method} ${call.path}`)).toEqual([
      `GET ${BASE}${TARGET}`,
      `PATCH ${BASE}${CURRENT}`,
    ]);
  });

  it.each([401, 403, 500])(
    "preserves target lookup upstream HTTP %s",
    async (status) => {
      failures.set(`GET ${BASE}${TARGET}`, {
        status,
        message: "Synthetic lookup failure",
      });
      expect(await request({ name: TARGET })).toEqual({
        status,
        body: {
          success: false,
          error: "Synthetic lookup failure",
          code: null,
          details: null,
        },
      });
      expect(mutations()).toEqual([]);
    },
  );
  it.each([401, 403, 404, 500])(
    "does not mistake source lookup HTTP %s for a free target",
    async (status) => {
      repos.set(TARGET, repository(TARGET));
      failures.set(`GET ${BASE}${CURRENT}`, {
        status,
        message: "Synthetic source lookup failure",
      });
      expect(await request({ name: TARGET })).toEqual({
        status,
        body: {
          success: false,
          error: "Synthetic source lookup failure",
          code: null,
          details: null,
        },
      });
      expect(mutations()).toEqual([]);
    },
  );
  it("preserves an upstream edit refusal after a valid self-redirect check", async () => {
    redirects.set(TARGET, CURRENT);
    failures.set(`PATCH ${BASE}${CURRENT}`, {
      status: 403,
      message: "Synthetic edit denied",
    });
    expect(await request({ name: TARGET })).toEqual({
      status: 403,
      body: {
        success: false,
        error: "Synthetic edit denied",
        code: null,
        details: null,
      },
    });
    expect(repos.get(CURRENT)).toEqual(repository(CURRENT));
  });

  it.each([{}, { name: null }, { name: CURRENT }, { name: "Books Temp" }])(
    "updates metadata without a duplicate probe for %j",
    async (name) => {
      const result = await request({
        ...name,
        description: "Updated synthetic description",
        private: false,
      });
      expect(result.status).toBe(200);
      expect(result.body).toMatchObject({
        success: true,
        data: {
          name: CURRENT,
          description: "Updated synthetic description",
          private: false,
        },
      });
      expect(calls).toHaveLength(1);
      expect(calls[0]).toMatchObject({
        method: "PATCH",
        path: `${BASE}${CURRENT}`,
      });
    },
  );

  it("retains create's duplicate refusal even for an old-name alias", async () => {
    redirects.set(TARGET, CURRENT);
    expect(
      await request({ name: TARGET, files: { "main.bean": FILE } }, "POST"),
    ).toEqual({ status: 400, body: conflict() });
    expect(mutations()).toEqual([]);
  });
  it.each([403, 500])(
    "retains create's mapped duplicate-check HTTP %s",
    async (status) => {
      failures.set(`GET ${BASE}${TARGET}`, {
        status,
        message: "Private upstream error",
      });
      expect(
        await request({ name: TARGET, files: { "main.bean": FILE } }, "POST"),
      ).toEqual({
        status,
        body: {
          success: false,
          error:
            status === 403
              ? "Permission denied while checking for duplicate ledger"
              : "Failed to check for duplicate ledger: (500)",
          code: null,
          details: null,
        },
      });
      expect(mutations()).toEqual([]);
    },
  );
  it("still creates an unused ledger, installs policy and writes its exact initial file", async () => {
    const result = await request(
      { name: "Books", files: { "main.bean": FILE }, private: true },
      "POST",
    );
    expect(result.status).toBe(201);
    expect(result.body).toMatchObject({
      success: true,
      data: { id: 71, name: TARGET, private: true },
    });
    expect(files).toEqual(new Map([["main.bean", FILE]]));
    expect(mutations().map((call) => `${call.method} ${call.path}`)).toEqual([
      "POST /api/v1/user/repos",
      `POST ${BASE}${TARGET}/contents`,
    ]);
  });
  it("denies missing authorization before any repository access", async () => {
    expect((await request({ name: TARGET }, "PUT", null)).status).toBe(401);
    expect(calls).toEqual([]);
  });
});
