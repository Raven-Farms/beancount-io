import http from "node:http";
import type { AddressInfo } from "node:net";
import Koa from "koa";
import cors from "@koa/cors";
import { resolveCorsOrigin } from "../cors-origin";

const SELF_HOST = new Set(["https://books.example.com"]);

describe("resolveCorsOrigin", () => {
  it.each([
    ["", "*"],
    ["https://beancount.io", "https://beancount.io"],
    ["https://dashboard.v3.beancount.io", "https://dashboard.v3.beancount.io"],
    ["http://localhost:5173", "http://localhost:5173"],
    ["http://127.0.0.1:42600", "http://127.0.0.1:42600"],
    ["https://books.example.com", "https://books.example.com"],
  ])("allows %j", (origin, expected) => {
    expect(resolveCorsOrigin(origin, SELF_HOST)).toBe(expected);
  });

  it.each([
    "http://books.example.com", // scheme mismatch
    "https://books.example.com:8443", // port mismatch
    "https://evil-books.example.com",
    "https://books.example.com.evil.test", // suffix lookalike
    "https://notbeancount.io",
    "https://beancount.io.evil.test",
    "null",
    "not a url",
  ])("refuses %j", (origin) => {
    expect(resolveCorsOrigin(origin, SELF_HOST)).toBe("");
  });

  it("keeps upstream behaviour when CORS_ALLOWED_ORIGINS is unset", () => {
    expect(resolveCorsOrigin("https://books.example.com", new Set())).toBe("");
    expect(resolveCorsOrigin("https://beancount.io", new Set())).toBe(
      "https://beancount.io",
    );
  });
});

describe("CORS middleware with resolveCorsOrigin", () => {
  let server: http.Server;
  let base: string;

  beforeAll(async () => {
    const app = new Koa();
    app.use(
      cors({
        origin: (ctx) => resolveCorsOrigin(ctx.get("Origin"), SELF_HOST),
        credentials: true,
      }),
    );
    app.use((ctx) => {
      ctx.body = { ok: true };
    });
    server = http.createServer(app.callback());
    await new Promise<void>((resolve) =>
      server.listen(0, "127.0.0.1", resolve),
    );
    base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  });

  afterAll(async () => {
    await new Promise((resolve) => server.close(resolve));
  });

  const preflight = (origin: string) =>
    fetch(`${base}/api-gateway/`, {
      method: "OPTIONS",
      headers: {
        Origin: origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
      },
    });

  it("answers a credentialed preflight from a configured self-host origin", async () => {
    const res = await preflight("https://books.example.com");
    expect(res.headers.get("access-control-allow-origin")).toBe(
      "https://books.example.com",
    );
    expect(res.headers.get("access-control-allow-credentials")).toBe("true");
  });

  it.each([
    "https://evil.test",
    "https://books.example.com.evil.test",
    "http://books.example.com",
  ])("sends no allow-origin header for %j", async (origin) => {
    const res = await preflight(origin);
    expect(res.headers.get("access-control-allow-origin")).toBeNull();
  });
});
