import http from "node:http";
import Koa from "koa";
import { trustProxyHops } from "../client-address";
import { createContext } from "../graphql/context";
import type { AppConfig } from "@/config/config";
import type { DatabaseLayer } from "@/foundation/composition";

// Every rate limiter keys on the caller's address: REST on `ctx.ip`, GraphQL on
// `IContext.clientIp`. Both used to take the left-most X-Forwarded-For entry,
// which is whatever the client sent, so rotating it bought a fresh budget
// (w0/m7). They now take the entry the nearest trusted proxy appended.

const database = {
  db: {},
  models: { jwt: { verify: jest.fn() }, user: { getById: jest.fn() } },
} as unknown as DatabaseLayer;

async function addressesSeen(hops: number, forwardedFor?: string) {
  const app = new Koa();
  trustProxyHops(app, hops);
  app.use(async (ctx) => {
    const context = await createContext(ctx, database, {} as AppConfig);
    ctx.body = { rest: ctx.ip, graphql: context.clientIp };
  });
  const server = http.createServer(app.callback());
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const { port } = server.address() as { port: number };
    const response = await fetch(`http://127.0.0.1:${port}/`, {
      headers: forwardedFor ? { "x-forwarded-for": forwardedFor } : {},
    });
    return (await response.json()) as { rest: string; graphql: string };
  } finally {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
}

const socket = (ip: string) => ip.replace(/^::ffff:/u, "");

describe("the client address every limiter keys on", () => {
  it("is the entry the one trusted proxy appended, on REST and GraphQL alike", async () => {
    // The client wrote 1.1.1.1; the proxy appended the address it saw.
    const seen = await addressesSeen(1, "1.1.1.1, 2.2.2.2");

    expect(seen).toEqual({ rest: "2.2.2.2", graphql: "2.2.2.2" });
  });

  it("does not move when the client rotates the entries it writes", async () => {
    const a = await addressesSeen(1, "1.1.1.1, 2.2.2.2");
    const b = await addressesSeen(1, "9.9.9.9, 8.8.8.8, 2.2.2.2");

    expect(b).toEqual(a);
  });

  it("counts back as many hops as are trusted", async () => {
    const seen = await addressesSeen(2, "1.1.1.1, 2.2.2.2, 3.3.3.3");

    expect(seen).toEqual({ rest: "2.2.2.2", graphql: "2.2.2.2" });
  });

  it("ignores the header when no proxy is trusted", async () => {
    const seen = await addressesSeen(0, "1.1.1.1, 2.2.2.2");

    expect(socket(seen.rest)).toBe("127.0.0.1");
    expect(socket(seen.graphql)).toBe("127.0.0.1");
  });

  it("falls back to the socket when the proxy sent no header", async () => {
    const seen = await addressesSeen(1);

    expect(socket(seen.rest)).toBe("127.0.0.1");
    expect(seen.graphql).toBe(seen.rest);
  });
});
