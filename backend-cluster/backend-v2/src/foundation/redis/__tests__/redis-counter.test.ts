import { incrementInWindow } from "../redis-counter";
import { getRedisClient } from "../redis-utils";
import { logger } from "@/shared/logger";

jest.mock("../redis-utils", () => ({ getRedisClient: jest.fn() }));
jest.mock("@/shared/logger", () => {
  const logs = { error: jest.fn() };
  return { logger: { child: () => logs } };
});

const clientMock = getRedisClient as jest.Mock;

function fakeRedis() {
  return { eval: jest.fn().mockResolvedValue([1, 60_000]) };
}

describe("incrementInWindow", () => {
  it("reports an unavailable counter when Redis is not initialized", async () => {
    clientMock.mockReturnValue(null);
    await expect(incrementInWindow("k", 60_000)).resolves.toBeUndefined();
  });

  it("increments and assigns expiry in one atomic command instead of separate writes", async () => {
    const redis = fakeRedis();
    clientMock.mockReturnValue(redis);

    await expect(incrementInWindow("k", 60_000)).resolves.toEqual({
      count: 1,
      resetInMs: 60_000,
    });
    expect(redis.eval).toHaveBeenCalledWith(expect.any(String), {
      keys: ["k"],
      arguments: ["60000"],
    });
    expect(redis.eval).toHaveBeenCalledTimes(1);
  });

  it("does not log Redis errors containing command keys or credentials", async () => {
    const redis = fakeRedis();
    redis.eval.mockRejectedValue(
      new Error("EVAL synthetic-private-key secret-command-value"),
    );
    clientMock.mockReturnValue(redis);

    await expect(
      incrementInWindow("synthetic-private-key", 60_000),
    ).resolves.toBeUndefined();
    const calls = jest.mocked(logger.child({ module: "test" }).error).mock
      .calls;
    expect(calls.at(-1)).toEqual(["Redis counter unavailable"]);
    expect(JSON.stringify(calls)).not.toContain("secret-command-value");
    expect(JSON.stringify(calls)).not.toContain("synthetic-private-key");
  });

  it.each([0, -1, NaN, Infinity, 1.5])(
    "rejects an invalid expiry before a command can leave an immortal counter: %s",
    async (windowMs) => {
      const redis = fakeRedis();
      clientMock.mockReturnValue(redis);
      await expect(
        incrementInWindow("invalid-window", windowMs),
      ).resolves.toBeUndefined();
      expect(redis.eval).not.toHaveBeenCalled();
    },
  );
});
