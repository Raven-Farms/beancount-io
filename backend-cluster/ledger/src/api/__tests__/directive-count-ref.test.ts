import http from "node:http";
import Koa from "koa";
import Router from "@koa/router";
import { setLedgersHandler } from "@/api/ledgers";
import { restErrorMiddleware } from "@/server/error-middleware";
import { countDirectivesForRepo } from "@/core/directive-limit";

// `GET …/directive-count?ref=` counts one commit, so backend-v2 can compare a
// pull request's head with its base before merging (w0/m6). The ref reaches
// Gitea and the file-map cache key, so only a commit SHA is accepted.

jest.mock("@/core/directive-limit", () => ({
  ...jest.requireActual("@/core/directive-limit"),
  countDirectivesForRepo: jest.fn(async () => ({ count: 7, sha: "abc1234" })),
}));

const countMock = countDirectivesForRepo as jest.Mock;
const AUTH = `Basic ${Buffer.from("alice:synthetic-password").toString("base64")}`;

let server: http.Server;
let base: string;

beforeAll(async () => {
  const router = new Router();
  setLedgersHandler(router);
  const app = new Koa();
  app.use(restErrorMiddleware()).use(router.routes());
  server = http.createServer(app.callback());
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  base = `http://127.0.0.1:${(server.address() as { port: number }).port}`;
});

afterAll(() => new Promise<void>((resolve) => server.close(() => resolve())));

beforeEach(() => countMock.mockClear());

const get = (query: string) =>
  fetch(`${base}/ledgers/alice/books/directive-count${query}`, {
    headers: { authorization: AUTH },
  });

describe("directive-count ref", () => {
  it("counts HEAD without a ref", async () => {
    const response = await get("");

    expect(response.status).toBe(200);
    expect(countMock).toHaveBeenCalledWith(
      expect.anything(),
      "alice",
      "books",
      undefined,
    );
  });

  it("counts the commit a SHA names", async () => {
    const sha = "0123456789abcdef0123456789abcdef01234567";

    const response = await get(`?ref=${sha}`);

    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({
      success: true,
      data: { count: 7 },
    });
    expect(countMock).toHaveBeenCalledWith(
      expect.anything(),
      "alice",
      "books",
      sha,
    );
  });

  it.each(["main", "HEAD", "abc", "../../etc", "0123456789abcdef!"])(
    "refuses %j, which is not a commit SHA",
    async (ref) => {
      const response = await get(`?ref=${encodeURIComponent(ref)}`);

      expect(response.status).toBe(400);
      expect(countMock).not.toHaveBeenCalled();
    },
  );
});
