const counter = jest.fn();
jest.mock("@/foundation/redis/redis-counter", () => ({
  incrementInWindow: (...args: unknown[]) => counter(...args),
}));

import {
  clearRateLimitShadows,
  consume,
  consumeAnonymous,
  enforceRateLimit,
  MCP_HANDSHAKE_OP_ID,
  MCP_TRANSPORT_OP_ID,
} from "@/server/api/rate-limit";
import type { Identity } from "@/server/api/identity";
import { restRateLimitMiddleware } from "@/server/rest/rate-limit-middleware";
import type { RouterContext } from "@koa/router";

const token: Identity = {
  userId: "usr_fixture",
  tokenId: "tok_fixture",
  method: "oauth",
  scopes: new Set(["ledger.read"]),
};
const read = (identity: Identity = token, opId = "GQL Query.listLedgers") =>
  consume({ opId, identity, ip: "192.0.2.1" });
const write = (
  identity: Identity = token,
  opId = "GQL Mutation.createApiKey",
) => consume({ opId, identity, ip: "192.0.2.1" });

beforeEach(() => {
  // Optional only so the saved pre-fix implementation can run the regression
  // cases independently; every shipped implementation exports this seam.
  clearRateLimitShadows?.();
  counter.mockReset();
  counter.mockImplementation(async (key: string) => {
    const count = (counts.get(key) ?? 0) + 1;
    counts.set(key, count);
    return { count, resetInMs: 60_000 };
  });
  counts.clear();
});
afterEach(() => jest.restoreAllMocks());
const counts = new Map<string, number>();

it("rotating credentials and protocols cannot multiply the user's operation allowance", async () => {
  const aliases = [
    "GQL Query.listLedgers",
    "REST GET /api-gateway/v1/ledgers",
    "MCP listLedgers",
  ];
  for (let index = 0; index < 300; index += 1) {
    const identity = {
      ...token,
      tokenId: `tok_${index % 3}`,
      method: index % 2 ? ("session" as const) : ("oauth" as const),
    };
    expect((await read(identity, aliases[index % 3])).allowed).toBe(true);
  }

  expect((await read({ ...token, tokenId: "brand-new-token" })).allowed).toBe(
    false,
  );
  expect(
    (
      await read({
        ...token,
        userId: "usr_independent",
        tokenId: "independent-token",
      })
    ).allowed,
  ).toBe(true);
});

it("retains the smaller override when a credential changes protocol", async () => {
  for (let index = 0; index < 5; index += 1)
    expect((await write()).allowed).toBe(true);
  expect(
    (await write(token, "REST POST /api-gateway/v1/api-keys")).allowed,
  ).toBe(false);
  expect((await read()).allowed).toBe(true);
});

it.each(["usr:", "tok:"])(
  "requires the independent %s budget even when the other Redis counter is unavailable",
  async (subject) => {
    counter.mockImplementation(async (key: string) =>
      key.includes(subject) ? { count: 6, resetInMs: 60_000 } : undefined,
    );

    expect((await write()).allowed).toBe(false);
  },
);

it("keeps already-spent healthy volume spent during outage", async () => {
  counter.mockResolvedValue({ count: 5, resetInMs: 60_000 });
  expect((await write()).allowed).toBe(true);
  counter.mockResolvedValue(undefined);

  expect((await write()).allowed).toBe(false);
});

it("preserves unpersisted local volume across outage and recovery", async () => {
  counter.mockResolvedValue(undefined);
  for (let index = 0; index < 4; index += 1)
    expect((await write()).allowed).toBe(true);
  counter.mockResolvedValue({ count: 1, resetInMs: 60_000 });
  expect((await write()).allowed).toBe(true);

  expect((await write()).allowed).toBe(false);
});

it("admits only the available local quota under concurrent outage requests", async () => {
  counter.mockResolvedValue(undefined);
  const decisions = await Promise.all(
    Array.from({ length: 100 }, () =>
      consume({
        opId: "GQL Mutation.unclassifiedWrite",
        identity: token,
        ip: "192.0.2.1",
      }),
    ),
  );

  expect(decisions.filter(({ allowed }) => allowed)).toHaveLength(60);
  expect(decisions.filter(({ allowed }) => !allowed)).toHaveLength(40);
});

it("bounds anonymous intake during outage and keeps device polling independent", async () => {
  counter.mockResolvedValue(undefined);
  for (let index = 0; index < 120; index += 1) {
    expect(
      (await consumeAnonymous({ path: "/api-gateway/other", ip: "192.0.2.1" }))
        .allowed,
    ).toBe(true);
  }
  expect(
    (await consumeAnonymous({ path: "/api-gateway/other", ip: "192.0.2.1" }))
      .allowed,
  ).toBe(false);
  for (let index = 0; index < 120; index += 1) {
    expect(
      (
        await consumeAnonymous({
          path: `/api-gateway/v1/cli-sessions/different-code-${index}`,
          ip: "192.0.2.1",
        })
      ).allowed,
    ).toBe(true);
  }
  expect(
    (
      await consumeAnonymous({
        path: "/api-gateway/v1/cli-sessions/new-code",
        ip: "192.0.2.1",
      })
    ).allowed,
  ).toBe(false);
  expect(
    (
      await consumeAnonymous({
        path: "/api-gateway/oauth/authorize",
        ip: "192.0.2.1",
      })
    ).allowed,
  ).toBe(true);
});

it("shares device polling across the router's case and trailing-slash aliases", async () => {
  counter.mockResolvedValue(undefined);
  const aliases = [
    "/api-gateway/v1/cli-sessions/code",
    "/api-gateway/v1/cli-sessions/code/",
    "/API-GATEWAY/V1/CLI-SESSIONS/code",
  ];
  for (let index = 0; index < 120; index += 1) {
    expect(
      (
        await consumeAnonymous({
          path: aliases[index % aliases.length],
          ip: "192.0.2.1",
        })
      ).allowed,
    ).toBe(true);
  }
  for (const path of aliases) {
    expect((await consumeAnonymous({ path, ip: "192.0.2.1" })).allowed).toBe(
      false,
    );
  }
  expect(
    (await consumeAnonymous({ path: "/api-gateway/other", ip: "192.0.2.1" }))
      .allowed,
  ).toBe(true);
});

it("keeps archive and OAuth router aliases on their own smaller anonymous budgets", async () => {
  counter.mockResolvedValue(undefined);
  const archive = "/api-gateway/v1/ledgers/owner/books/archive/main.zip";
  for (let index = 0; index < 30; index += 1) {
    expect(
      (await consumeAnonymous({ path: archive, ip: "192.0.2.1" })).allowed,
    ).toBe(true);
  }
  expect(
    (
      await consumeAnonymous({
        path: `${archive.toUpperCase()}/`,
        ip: "192.0.2.1",
      })
    ).allowed,
  ).toBe(false);
  for (let index = 0; index < 60; index += 1) {
    expect(
      (
        await consumeAnonymous({
          path: "/api-gateway/oauth/authorize",
          ip: "192.0.2.1",
        })
      ).allowed,
    ).toBe(true);
  }
  expect(
    (
      await consumeAnonymous({
        path: "/API-GATEWAY/OAUTH/AUTHORIZE/",
        ip: "192.0.2.1",
      })
    ).allowed,
  ).toBe(false);
  expect(
    (await consumeAnonymous({ path: "/api-gateway/other", ip: "192.0.2.1" }))
      .allowed,
  ).toBe(true);
});

it("keeps handshake, ordinary transport, refresh and password operations in distinct buckets", async () => {
  counter.mockResolvedValue(undefined);
  for (let index = 0; index < 300; index += 1)
    expect((await read(token, MCP_TRANSPORT_OP_ID)).allowed).toBe(true);
  expect((await read(token, MCP_TRANSPORT_OP_ID)).allowed).toBe(false);
  expect((await read(token, MCP_HANDSHAKE_OP_ID)).allowed).toBe(true);
  expect((await read(token, "GQL Mutation.refreshToken")).allowed).toBe(true);
  expect((await read(token, "GQL Mutation.signIn")).allowed).toBe(true);
});

it("resets fixed shadow generations without extending them through healthy traffic", async () => {
  let now = 1_000;
  jest.spyOn(Date, "now").mockImplementation(() => now);
  counter.mockResolvedValue({ count: 1, resetInMs: 60_000 });
  for (let window = 0; window < 3; window += 1) {
    for (let index = 0; index < 5; index += 1) {
      expect((await write()).allowed).toBe(true);
      now += 10_000;
    }
    now = 1_000 + (window + 1) * 60_000;
  }
  counter.mockResolvedValue(undefined);

  expect((await write()).allowed).toBe(true);
});

it("does not let a delayed prior-generation Redis reply poison the current window", async () => {
  let now = 1_000;
  jest.spyOn(Date, "now").mockImplementation(() => now);
  let finish!: (value: { count: number; resetInMs: number }) => void;
  counter.mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const old = write({ ...token, tokenId: undefined });
  now += 60_001;
  counter.mockResolvedValue(undefined);
  expect((await write({ ...token, tokenId: undefined })).allowed).toBe(true);
  finish({ count: 100, resetInMs: 60_000 });
  await old;

  for (let index = 0; index < 4; index += 1)
    expect((await write({ ...token, tokenId: undefined })).allowed).toBe(true);
  expect((await write({ ...token, tokenId: undefined })).allowed).toBe(false);
});

it("does not evict live entries at capacity and admits fresh subjects after expiry", async () => {
  let now = 1_000;
  jest.spyOn(Date, "now").mockImplementation(() => now);
  counter.mockResolvedValue(undefined);
  const known = { ...token, tokenId: undefined };
  expect((await read(known)).allowed).toBe(true);
  for (let index = 0; index < 9_999; index += 1) {
    expect(
      (
        await consumeAnonymous({
          path: "/api-gateway/other",
          ip: `synthetic-${index}`,
        })
      ).allowed,
    ).toBe(true);
  }
  for (let index = 0; index < 20; index += 1) {
    expect(
      (await read({ ...token, userId: `new-${index}`, tokenId: undefined }))
        .allowed,
    ).toBe(false);
  }
  for (let index = 0; index < 299; index += 1)
    expect((await read(known)).allowed).toBe(true);
  expect((await read(known)).allowed).toBe(false);
  now += 60_001;

  expect(
    (await read({ ...token, userId: "new-after-expiry", tokenId: undefined }))
      .allowed,
  ).toBe(true);
});

it("does not allocate fresh credential shadows after the user total is spent", async () => {
  counter.mockResolvedValue(undefined);
  for (let index = 0; index < 5; index += 1)
    expect((await write()).allowed).toBe(true);
  for (let index = 0; index < 10_000; index += 1) {
    expect(
      (await write({ ...token, tokenId: `rotated-${index}` })).allowed,
    ).toBe(false);
  }

  expect(
    (await write({ ...token, userId: "independent", tokenId: "independent" }))
      .allowed,
  ).toBe(true);
});

it("returns generic retry information without naming which budget refused", async () => {
  counter.mockResolvedValue({ count: 301, resetInMs: 60_000 });

  await expect(
    enforceRateLimit({
      opId: "GQL Query.listLedgers",
      identity: token,
      ip: "192.0.2.1",
    }),
  ).rejects.toMatchObject({
    message: "Too many requests. Please try again later.",
    metadata: { retryAfter: 60 },
  });
});

it("sets authenticated REST Retry-After before invoking the handler", async () => {
  counter.mockResolvedValue({ count: 301, resetInMs: 60_000 });
  const set = jest.fn();
  const next = jest.fn(async () => {});
  const ctx = {
    method: "POST",
    path: "/api-gateway/mcp",
    ip: "192.0.2.1",
    state: { identity: token },
    request: { body: {} },
    matched: [{ methods: ["POST"], path: "/api-gateway/mcp" }],
    set,
  } as unknown as RouterContext;

  await expect(restRateLimitMiddleware()(ctx, next)).rejects.toMatchObject({
    category: "RATE_LIMITED",
  });
  expect(set).toHaveBeenCalledWith("Retry-After", "60");
  expect(next).not.toHaveBeenCalled();
});
