import http from "node:http";
import { Readable } from "node:stream";
import Koa from "koa";
import Router from "@koa/router";
import type { AppConfig } from "@/config/config";
import type { AppLayers } from "@/foundation/composition";
import type { Identity } from "@/server/api/identity";
import { BadUserInputError } from "@/shared/errors";
import { restErrorMiddleware } from "../error-middleware";
import { registerV1Routes, v1Route, type V1Route } from "../v1-route";

const bytes = Buffer.from([80, 75, 3, 4, 0, 255]);
const positive = { date: "2017-08-23", amount: "80.08", narration: "" };
const identity: Identity = {
  userId: "usr_response",
  method: "session",
  scopes: new Set(),
};

function route(name: string, handler: V1Route["handler"]) {
  return v1Route({
    method: "get",
    path: `/api-gateway/v1/response/${name}`,
    summary: "Synthetic response boundary",
    description:
      "Exercise the shared value/custom-response boundary over HTTP.",
    responses: { 200: { description: "Synthetic response" } },
    handler,
  });
}

describe("v1 route response ownership over HTTP", () => {
  let server: http.Server;
  let base: string;

  beforeAll(async () => {
    const router = new Router();
    router.use(restErrorMiddleware());
    router.use(async (ctx, next) => {
      ctx.state.identity = identity;
      await next();
    });
    registerV1Routes(
      router,
      { layers: {} as AppLayers, config: {} as AppConfig },
      [
        route("null", async () => null),
        route("object", async () => positive),
        route("custom-text", async (_deps, { ctx }) => {
          ctx.status = 202;
          ctx.type = "text/plain";
          ctx.set("X-Response-Owner", "handler");
          ctx.body = "accepted\n";
          return undefined;
        }),
        ...["buffer", "stream"].map((kind) =>
          route(`custom-${kind}`, async (_deps, { ctx }) => {
            ctx.status = 206;
            ctx.type = "application/zip";
            ctx.attachment("synthetic.zip");
            ctx.set(
              "Content-Range",
              `bytes 0-${bytes.length - 1}/${bytes.length}`,
            );
            ctx.body = kind === "buffer" ? bytes : Readable.from([bytes]);
            return undefined;
          }),
        ),
        route("returned-buffer", async () => bytes),
        route("returned-stream", async () => Readable.from([bytes])),
        route("domain-error", async () => {
          throw new BadUserInputError("Invalid synthetic query", "query");
        }),
        route("unexpected-error", async () => {
          throw new Error("Synthetic upstream failure");
        }),
      ],
    );
    const app = new Koa();
    app.silent = true;
    app.use(router.routes()).use(router.allowedMethods());
    server = http.createServer(app.callback());
    await new Promise<void>((resolve) =>
      server.listen(0, "127.0.0.1", resolve),
    );
    const address = server.address();
    if (!address || typeof address === "string")
      throw new Error("Expected a local HTTP server address");
    base = `http://127.0.0.1:${address.port}/api-gateway/v1/response`;
  });

  afterAll(async () => {
    if (server) {
      server.closeAllConnections();
      await new Promise<void>((resolve, reject) =>
        server.close((error) => (error ? reject(error) : resolve())),
      );
    }
  });

  const request = (name: string) =>
    fetch(`${base}/${name}`, { signal: AbortSignal.timeout(3000) });

  it("returns a defined null as status 200 and parseable JSON null", async () => {
    const response = await request("null");
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toMatch(
      /^application\/json\b/,
    );
    expect(await response.clone().text()).toBe("null");
    expect(await response.json()).toBeNull();
  });

  it("preserves the ordinary positive object response", async () => {
    const response = await request("object");
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toMatch(
      /^application\/json\b/,
    );
    expect(await response.json()).toEqual(positive);
  });

  it("leaves a handler-owned status, type and body intact when it returns undefined", async () => {
    const response = await request("custom-text");
    expect(response.status).toBe(202);
    expect(response.headers.get("content-type")).toMatch(/^text\/plain\b/);
    expect(response.headers.get("x-response-owner")).toBe("handler");
    expect(await response.text()).toBe("accepted\n");
  });

  it.each(["buffer", "stream"])(
    "preserves a custom %s response and its archive headers",
    async (kind) => {
      const response = await request(`custom-${kind}`);
      expect(response.status).toBe(206);
      expect(response.headers.get("content-type")).toMatch(
        /^application\/zip\b/,
      );
      expect(response.headers.get("content-disposition")).toBe(
        'attachment; filename="synthetic.zip"',
      );
      expect(response.headers.get("content-range")).toBe("bytes 0-5/6");
      expect(Buffer.from(await response.arrayBuffer())).toEqual(bytes);
    },
  );

  it.each(["buffer", "stream"])(
    "keeps a directly returned %s as bytes",
    async (kind) => {
      const response = await request(`returned-${kind}`);
      expect(response.status).toBe(200);
      expect(response.headers.get("content-type")).toBe(
        "application/octet-stream",
      );
      expect(Buffer.from(await response.arrayBuffer())).toEqual(bytes);
    },
  );

  it.each([
    { name: "domain-error", status: 400, code: "BAD_USER_INPUT" },
    { name: "unexpected-error", status: 500, code: "INTERNAL_SERVER_ERROR" },
  ])("retains the $name failure instead of returning null", async (entry) => {
    const response = await request(entry.name);
    expect(response.status).toBe(entry.status);
    expect(response.headers.get("content-type")).toMatch(
      /^application\/json\b/,
    );
    expect(await response.json()).toMatchObject({
      ok: false,
      error: { code: entry.code },
    });
  });
});
