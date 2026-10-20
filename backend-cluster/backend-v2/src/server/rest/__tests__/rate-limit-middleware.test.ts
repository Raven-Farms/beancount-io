const counter = jest.fn();
jest.mock("@/foundation/redis/redis-counter", () => ({
  incrementInWindow: (...args: unknown[]) => counter(...args),
}));

import type { RouterContext } from "@koa/router";
import { restRateLimitMiddleware } from "../rate-limit-middleware";
import {
  MCP_HANDSHAKE_OP_ID,
  MCP_TRANSPORT_OP_ID,
  OP_BUDGETS,
  clearRouteRateLimitPolicies,
  clearRateLimitShadows,
  setRouteRateLimitPolicy,
} from "@/server/api/rate-limit";
import { mcpRateLimitPolicy } from "@/features/ai-agent/api/mcp-rate-policy";
import { RateLimitedError } from "@/shared/errors";
import type { Identity } from "@/server/api/identity";

/**
 * w2/m28:t004. The middleware half of the MCP transport budget: an agent
 * session is dozens of POSTs to one path, and the handshake is protocol
 * overhead the caller did not choose.
 */
const identity: Identity = {
  userId: "usr_1",
  method: "oauth",
  scopes: new Set(["ledger.read"]),
  tokenId: "tok_1",
};

/** A Koa context matched to the MCP mount, carrying `body` as its payload. */
function mcpContext(body: unknown): RouterContext {
  return {
    method: "POST",
    path: "/api-gateway/mcp",
    ip: "10.0.0.1",
    state: { identity },
    request: { body },
    matched: [{ methods: ["POST"], path: "/api-gateway/mcp" }],
    set: jest.fn(),
  } as unknown as RouterContext;
}

beforeEach(() => {
  clearRateLimitShadows();
  counter.mockReset();
  counter.mockResolvedValue({ count: 1, resetInMs: 60_000 });
  // Installed by mounting the route in production (w2/014); the middleware
  // itself knows nothing about MCP.
  setRouteRateLimitPolicy(MCP_TRANSPORT_OP_ID, mcpRateLimitPolicy);
});

afterEach(() => clearRouteRateLimitPolicies());

describe("the MCP transport budget", () => {
  it("charges a handshake message to the handshake bucket, not the session's", async () => {
    // Not free — a total exemption let unlimited `{"method":"ping"}` posts
    // cost a credential nothing (w2/014) — but spent somewhere that cannot
    // eat the session's allowance.
    const next = jest.fn(async () => {});
    await restRateLimitMiddleware()(
      mcpContext({ jsonrpc: "2.0", method: "initialize", id: 1 }),
      next,
    );
    expect(counter).toHaveBeenCalledTimes(2);
    expect(counter.mock.calls[0][0]).toContain(MCP_HANDSHAKE_OP_ID);
    expect(next).toHaveBeenCalled();
  });

  it("knows nothing about MCP without the mount's policy", async () => {
    clearRouteRateLimitPolicies();
    await restRateLimitMiddleware()(
      mcpContext({ jsonrpc: "2.0", method: "initialize", id: 1 }),
      async () => {},
    );
    expect(counter.mock.calls[0][0]).toContain(MCP_TRANSPORT_OP_ID);
  });

  it("charges a tool call", async () => {
    await restRateLimitMiddleware()(
      mcpContext({ jsonrpc: "2.0", method: "tools/call", id: 2 }),
      async () => {},
    );
    expect(counter).toHaveBeenCalledTimes(2);
  });

  /** The acceptance criterion, run rather than argued. */
  it("lets a 200-read session through without a 429", async () => {
    const budget = OP_BUDGETS[MCP_TRANSPORT_OP_ID];
    const counts = new Map<string, number>();
    counter.mockImplementation(async (key: string) => {
      const count = (counts.get(key) ?? 0) + 1;
      counts.set(key, count);
      return { count, resetInMs: 60_000 };
    });

    const middleware = restRateLimitMiddleware();
    // One handshake, then 200 reads — the shape of the session that 429'd.
    // The handshake spends its own bucket, so it does not count here.
    await middleware(
      mcpContext({ jsonrpc: "2.0", method: "initialize", id: 0 }),
      async () => {},
    );
    for (let call = 0; call < 200; call += 1) {
      await expect(
        middleware(
          mcpContext({ jsonrpc: "2.0", method: "tools/call", id: call }),
          async () => {},
        ),
      ).resolves.not.toThrow();
    }
    const workCounts = [...counts.entries()].filter(
      ([key]) =>
        key.includes(MCP_TRANSPORT_OP_ID) && !key.includes("#handshake"),
    );
    expect(workCounts).toHaveLength(2);
    expect(workCounts.map(([, count]) => count)).toEqual([200, 200]);
    expect(workCounts.every(([, count]) => count <= budget.max)).toBe(true);
  });

  it("still refuses a caller past the transport budget", async () => {
    counter.mockResolvedValue({
      count: OP_BUDGETS[MCP_TRANSPORT_OP_ID].max + 1,
      resetInMs: 30_000,
    });
    await expect(
      restRateLimitMiddleware()(
        mcpContext({ jsonrpc: "2.0", method: "tools/call", id: 1 }),
        async () => {},
      ),
    ).rejects.toBeInstanceOf(RateLimitedError);
  });

  it("sets Retry-After when its own authenticated admission refuses before the handler", async () => {
    counter.mockResolvedValue({
      count: OP_BUDGETS[MCP_TRANSPORT_OP_ID].max + 1,
      resetInMs: 30_000,
    });
    const ctx = mcpContext({ jsonrpc: "2.0", method: "tools/call", id: 1 });
    const next = jest.fn(async () => {});

    await expect(restRateLimitMiddleware()(ctx, next)).rejects.toMatchObject({
      metadata: { retryAfter: 60 },
    });

    expect(ctx.set).toHaveBeenCalledWith("Retry-After", "60");
    expect(next).not.toHaveBeenCalled();
  });
});
