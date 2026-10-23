import http from "node:http";
import Koa from "koa";
import Router from "@koa/router";
import bodyParser from "koa-bodyparser";
import { setReportsHandler } from "@/api/reports";
import { restErrorMiddleware } from "@/server/error-middleware";

// w23/060: an append locates the directives it committed by file and line.
// The engine's resolution is covered by the service and resolver tests; this
// is the route: input checks, line → range, and the response shape.
const calls: {
  overlays: unknown[];
  ranges: { file: string; startLine: number; lineCount: number }[];
}[] = [];

jest.mock("@/server/auth", () => ({
  authMiddleware: async (_ctx: unknown, next: () => Promise<void>) => next(),
}));

jest.mock("../service-context", () => ({
  ...jest.requireActual("../service-context"),
  servicesForRequest: () => ({
    data: {
      projectedEntryIds: async (params: (typeof calls)[number]) => {
        calls.push(params);
        return params.ranges.map(({ file, startLine }) =>
          file === "main.bean" ? `id-${startLine}` : null,
        );
      },
    },
  }),
}));

describe("POST /reports/{o}/{r}/entry-ids", () => {
  let server: http.Server;
  let url: string;

  beforeAll(async () => {
    const app = new Koa();
    const router = new Router();
    setReportsHandler(router);
    app.use(restErrorMiddleware());
    app.use(bodyParser());
    app.use(router.routes());
    server = http.createServer(app.callback());
    await new Promise<void>((resolve) =>
      server.listen(0, "127.0.0.1", resolve),
    );
    url = `http://127.0.0.1:${(server.address() as { port: number }).port}`;
  });

  afterAll(() => new Promise<void>((resolve) => server.close(() => resolve())));

  beforeEach(() => {
    calls.length = 0;
  });

  const post = (body: unknown) =>
    fetch(`${url}/reports/alice/books/entry-ids`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });

  it("resolves each 1-based line over the projected files, in order", async () => {
    const files = [{ path: "main.bean", content: "Zm9v" }];
    const response = await post({
      files,
      locations: [
        { path: "main.bean", line: 12 },
        { path: "other.bean", line: 1 },
      ],
    });

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      success: true,
      data: { entry_hashes: ["id-11", null] },
    });
    expect(calls).toEqual([
      {
        ledgerId: "alice/books",
        userId: undefined,
        overlays: files,
        ranges: [
          { file: "main.bean", startLine: 11, lineCount: 1 },
          { file: "other.bean", startLine: 0, lineCount: 1 },
        ],
      },
    ]);
  });

  it.each([
    [{ locations: [{ path: "main.bean", line: 0 }] }, "1-based line"],
    [{ locations: [{ path: "main.bean", line: 1.5 }] }, "1-based line"],
    [{ locations: [{ line: 3 }] }, "must name a path"],
    [{ locations: "main.bean:3" }, "at most 200"],
    [
      {
        locations: Array.from({ length: 201 }, () => ({
          path: "main.bean",
          line: 1,
        })),
      },
      "at most 200",
    ],
  ])("refuses %j", async (body, message) => {
    const response = await post(body);
    expect(response.status).toBe(400);
    expect(((await response.json()) as { error: string }).error).toContain(
      message,
    );
    expect(calls).toEqual([]);
  });
});
