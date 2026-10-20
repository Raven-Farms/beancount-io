import { redisGoogleStateStore } from "../google-state-store";
import { getRedisClient } from "@/foundation/redis/redis-utils";

jest.mock("@/foundation/redis/redis-utils", () => ({
  getRedisClient: jest.fn(),
}));

/**
 * A fake with Redis's semantics for the two commands the store uses:
 * SET ... NX PX (only if absent, with expiry) and GETDEL (read and delete in
 * one step). Time is the jest clock, so expiry is real.
 */
function fakeRedis() {
  const data = new Map<string, { value: string; expiresAt: number }>();
  const live = (key: string) => {
    const entry = data.get(key);
    if (entry && entry.expiresAt <= Date.now()) data.delete(key);
    return data.get(key);
  };
  return {
    data,
    set: jest.fn(
      async (key: string, value: string, opts: { PX: number; NX: true }) => {
        if (opts.NX && live(key)) return null;
        data.set(key, { value, expiresAt: Date.now() + opts.PX });
        return "OK";
      },
    ),
    getDel: jest.fn(async (key: string) => {
      const entry = live(key);
      data.delete(key);
      return entry ? entry.value : null;
    }),
  };
}

const record = { nonce: "n", codeVerifier: "v", next: "/x" };

describe("redisGoogleStateStore", () => {
  let redis: ReturnType<typeof fakeRedis>;
  beforeEach(() => {
    jest.useFakeTimers();
    redis = fakeRedis();
    jest.mocked(getRedisClient).mockReturnValue(redis as never);
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it("stores with NX and a 10-minute expiry, and consumes with GETDEL", async () => {
    await redisGoogleStateStore.put("s1", record);
    expect(redis.set).toHaveBeenCalledWith(
      "auth:google_state:s1",
      JSON.stringify(record),
      { PX: 600_000, NX: true },
    );
    expect(await redisGoogleStateStore.consume("s1")).toEqual(record);
    expect(redis.getDel).toHaveBeenCalledWith("auth:google_state:s1");
  });

  it("redeems a state once, even when two callbacks race", async () => {
    await redisGoogleStateStore.put("s1", record);
    const [a, b] = await Promise.all([
      redisGoogleStateStore.consume("s1"),
      redisGoogleStateStore.consume("s1"),
    ]);
    expect([a, b].filter(Boolean)).toHaveLength(1);
    expect(await redisGoogleStateStore.consume("s1")).toBeNull();
  });

  it("forgets a state after ten minutes", async () => {
    await redisGoogleStateStore.put("s1", record);
    jest.advanceTimersByTime(600_001);
    expect(await redisGoogleStateStore.consume("s1")).toBeNull();
  });

  it("refuses to overwrite an existing state", async () => {
    await redisGoogleStateStore.put("s1", record);
    await expect(redisGoogleStateStore.put("s1", record)).rejects.toThrow(
      /not stored/,
    );
  });

  it("treats a malformed record as absent", async () => {
    redis.data.set("auth:google_state:s1", {
      value: JSON.stringify({ nonce: "n" }),
      expiresAt: Date.now() + 1000,
    });
    expect(await redisGoogleStateStore.consume("s1")).toBeNull();
  });

  it("fails closed without Redis", async () => {
    jest.mocked(getRedisClient).mockReturnValue(null);
    await expect(redisGoogleStateStore.put("s1", record)).rejects.toThrow(
      /Redis unavailable/,
    );
    await expect(redisGoogleStateStore.consume("s1")).rejects.toThrow(
      /Redis unavailable/,
    );
  });

  it("propagates Redis errors instead of treating them as success", async () => {
    redis.set.mockRejectedValueOnce(new Error("connection reset"));
    await expect(redisGoogleStateStore.put("s1", record)).rejects.toThrow(
      /connection reset/,
    );
    redis.getDel.mockRejectedValueOnce(new Error("connection reset"));
    await expect(redisGoogleStateStore.consume("s1")).rejects.toThrow(
      /connection reset/,
    );
  });
});
