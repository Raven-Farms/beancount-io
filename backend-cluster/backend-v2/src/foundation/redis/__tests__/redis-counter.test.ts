import { incrementInWindow, peekCount, resetCount } from "../redis-counter";
import { getRedisClient } from "../redis-utils";

// A budget checked before the attempt it counts needs to read a counter without
// spending it, and a success needs to end it early (w0/m7's password budget).

jest.mock("../redis-utils", () => ({ getRedisClient: jest.fn() }));
jest.mock("@/shared/logger", () => ({
  logger: { child: () => ({ error: jest.fn() }) },
}));

const clientMock = getRedisClient as jest.Mock;

function fakeRedis() {
  const values = new Map<string, number>();
  const expiries = new Map<string, number>();
  return {
    incr: jest.fn(async (key: string) => {
      const next = (values.get(key) ?? 0) + 1;
      values.set(key, next);
      return next;
    }),
    pExpire: jest.fn(async (key: string, ms: number) => {
      expiries.set(key, ms);
    }),
    pTTL: jest.fn(async (key: string) => expiries.get(key) ?? -2),
    get: jest.fn(async (key: string) =>
      values.has(key) ? String(values.get(key)) : null,
    ),
    del: jest.fn(async (key: string) => {
      const had = values.delete(key);
      expiries.delete(key);
      return had ? 1 : 0;
    }),
  };
}

describe("peekCount and resetCount", () => {
  it("reads a counter without spending it", async () => {
    const redis = fakeRedis();
    clientMock.mockReturnValue(redis);
    await incrementInWindow("k", 60_000);
    await incrementInWindow("k", 60_000);

    await expect(peekCount("k")).resolves.toEqual({
      count: 2,
      resetInMs: 60_000,
    });
    await expect(peekCount("k")).resolves.toMatchObject({ count: 2 });
  });

  it("reads zero for a counter that does not exist", async () => {
    clientMock.mockReturnValue(fakeRedis());

    await expect(peekCount("absent")).resolves.toEqual({
      count: 0,
      resetInMs: 0,
    });
  });

  it("ends a window early, so the next increment starts it again", async () => {
    const redis = fakeRedis();
    clientMock.mockReturnValue(redis);
    await incrementInWindow("k", 60_000);
    await incrementInWindow("k", 60_000);

    await resetCount("k");

    await expect(peekCount("k")).resolves.toMatchObject({ count: 0 });
    await expect(incrementInWindow("k", 60_000)).resolves.toMatchObject({
      count: 1,
    });
  });

  it("reports unknown, not zero, when Redis is unreachable", async () => {
    clientMock.mockReturnValue(null);
    await expect(peekCount("k")).resolves.toBeUndefined();
    await expect(resetCount("k")).resolves.toBeUndefined();

    const failing = fakeRedis();
    failing.get.mockRejectedValue(new Error("ECONNRESET"));
    failing.del.mockRejectedValue(new Error("ECONNRESET"));
    clientMock.mockReturnValue(failing);
    await expect(peekCount("k")).resolves.toBeUndefined();
    await expect(resetCount("k")).resolves.toBeUndefined();
  });
});
