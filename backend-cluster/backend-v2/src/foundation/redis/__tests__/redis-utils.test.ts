import {
  createRedisCache,
  closeRedisCache,
  getRedisClient,
} from "../redis-utils";

// Mock dependencies before they are used by the module
jest.mock("@keyv/redis");
jest.mock("keyv");
jest.mock("cache-manager");
jest.mock("@/shared/lock");

import KeyvRedis from "@keyv/redis";
import Keyv from "keyv";
import { createCache } from "cache-manager";
import { lock } from "@/shared/lock";

const MockKeyvRedis = KeyvRedis as jest.MockedClass<typeof KeyvRedis>;
const MockKeyv = Keyv as jest.MockedClass<typeof Keyv>;
const mockCreateCache = createCache as jest.MockedFunction<typeof createCache>;
const mockLock = lock as jest.Mocked<typeof lock>;

describe("redis-utils", () => {
  let mockCacheInstance: {
    set: jest.Mock;
    get: jest.Mock;
    del: jest.Mock;
  };
  let mockKeyvRedisInstance: {
    disconnect: jest.Mock;
    client: { isReady: boolean; eval: jest.Mock };
  };

  beforeEach(() => {
    jest.clearAllMocks();

    mockCacheInstance = {
      set: jest.fn().mockResolvedValue(undefined),
      get: jest.fn().mockResolvedValue("ok"),
      del: jest.fn().mockResolvedValue(undefined),
    };

    mockKeyvRedisInstance = {
      disconnect: jest.fn().mockResolvedValue(undefined),
      client: { isReady: true, eval: jest.fn().mockResolvedValue("value") },
    };

    MockKeyvRedis.mockImplementation(() => mockKeyvRedisInstance as never);
    MockKeyv.mockImplementation(() => ({}) as never);
    mockCreateCache.mockReturnValue(mockCacheInstance as never);

    // Mock lock.acquire to immediately execute the callback
    mockLock.acquire = jest
      .fn()
      .mockImplementation((_key: string, fn: () => Promise<unknown>) => fn());
  });

  afterEach(async () => {
    // Reset singleton state after each test
    await closeRedisCache();
    jest.useRealTimers();
  });

  describe("createRedisCache", () => {
    it("should throw when Redis URI is empty", async () => {
      await expect(createRedisCache("")).rejects.toThrow(
        "Redis URI required: ensure 'config.redis.uri' is set",
      );
    });

    it("should create and return a cache instance", async () => {
      const cache = await createRedisCache("redis://localhost:6379");

      expect(cache).toBeDefined();
      expect(MockKeyvRedis).toHaveBeenCalledWith(
        {
          url: "redis://localhost:6379",
          disableOfflineQueue: true,
          commandsQueueMaxLength: 256,
          commandOptions: { timeout: 1000 },
          socket: {
            connectTimeout: 2000,
            socketTimeout: 2000,
            reconnectStrategy: expect.any(Function),
          },
          pingInterval: 1000,
        },
        { throwOnErrors: true, connectionTimeout: 2000 },
      );
      expect(mockCreateCache).toHaveBeenCalled();
    });

    it("should use singleton pattern and return the same instance on subsequent calls", async () => {
      const cache1 = await createRedisCache("redis://localhost:6379");
      const cache2 = await createRedisCache("redis://localhost:6379");

      expect(cache1).toBe(cache2);
      // createCache should only be called once due to singleton
      expect(mockCreateCache).toHaveBeenCalledTimes(1);
    });

    it("should use the provided namespace when creating the Keyv instance", async () => {
      await createRedisCache("redis://localhost:6379", "my-namespace");

      expect(MockKeyv).toHaveBeenCalledWith(
        expect.objectContaining({
          namespace: "my-namespace",
          throwOnErrors: true,
        }),
      );
    });

    it("should use default namespace 'backend-v2' when not provided", async () => {
      await createRedisCache("redis://localhost:6379");

      expect(MockKeyv).toHaveBeenCalledWith(
        expect.objectContaining({ namespace: "backend-v2" }),
      );
    });

    it("should configure a type-preserving serializer/deserializer on Keyv", async () => {
      await createRedisCache("redis://localhost:6379");

      expect(MockKeyv).toHaveBeenCalledWith(
        expect.objectContaining({
          serialize: expect.any(Function),
          deserialize: expect.any(Function),
        }),
      );
    });

    it("should validate the connection by setting and getting a test key", async () => {
      await createRedisCache("redis://localhost:6379");

      expect(mockCacheInstance.set).toHaveBeenCalledWith(
        "__connection_test__",
        "ok",
        1000,
      );
      expect(mockCacheInstance.get).toHaveBeenCalledWith("__connection_test__");
      expect(mockCacheInstance.del).toHaveBeenCalledWith("__connection_test__");
    });

    it("should throw and clean up when connection validation fails (value mismatch)", async () => {
      mockCacheInstance.get.mockResolvedValue("wrong-value");

      await expect(createRedisCache("redis://localhost:6379")).rejects.toThrow(
        "Redis connection validation failed",
      );

      expect(mockKeyvRedisInstance.disconnect).toHaveBeenCalled();
    });

    it("should throw and clean up when cache.set throws", async () => {
      mockCacheInstance.set.mockRejectedValue(new Error("ECONNREFUSED"));

      await expect(createRedisCache("redis://localhost:6379")).rejects.toThrow(
        "Redis connection validation failed",
      );

      expect(mockKeyvRedisInstance.disconnect).toHaveBeenCalled();
    });

    it("should use lock to prevent concurrent initialization", async () => {
      await createRedisCache("redis://localhost:6379");

      expect(mockLock.acquire).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(Function),
      );
    });
  });

  describe("bounded atomic commands", () => {
    it("retains slots after caller deadlines until underlying commands settle", async () => {
      jest.useFakeTimers();
      const pending: {
        resolve: (value: string) => void;
        reject: (error: Error) => void;
      }[] = [];
      mockKeyvRedisInstance.client.eval.mockImplementation(
        () =>
          new Promise<string>((resolve, reject) =>
            pending.push({ resolve, reject }),
          ),
      );
      await createRedisCache("redis://localhost:6379");
      const redis = getRedisClient()!;
      const results = Promise.allSettled(
        Array.from({ length: 128 }, () =>
          redis.eval("synthetic", { keys: [], arguments: [] }),
        ),
      );
      await expect(
        redis.eval("overflow", { keys: [], arguments: [] }),
      ).rejects.toThrow("capacity");
      expect(mockKeyvRedisInstance.client.eval).toHaveBeenCalledTimes(128);
      await jest.advanceTimersByTimeAsync(1000);
      expect(
        (await results).every((result) => result.status === "rejected"),
      ).toBe(true);
      for (let attempt = 0; attempt < 100; attempt++)
        await expect(
          redis.eval("still full", { keys: [], arguments: [] }),
        ).rejects.toThrow("capacity");
      expect(mockKeyvRedisInstance.client.eval).toHaveBeenCalledTimes(128);

      pending[0].resolve("late reply");
      await Promise.resolve();
      mockKeyvRedisInstance.client.eval.mockResolvedValueOnce("recovered");
      await expect(
        redis.eval("available slot", { keys: [], arguments: [] }),
      ).resolves.toBe("recovered");
      for (const command of pending.slice(1))
        command.reject(new Error("late socket failure"));
      await Promise.resolve();
      expect(jest.getTimerCount()).toBe(0);
    });

    it("fails offline calls immediately without queuing, then permits recovery", async () => {
      await createRedisCache("redis://localhost:6379");
      const redis = getRedisClient()!;
      mockKeyvRedisInstance.client.isReady = false;
      await expect(
        redis.eval("offline", { keys: [], arguments: [] }),
      ).rejects.toThrow("unavailable");
      expect(mockKeyvRedisInstance.client.eval).not.toHaveBeenCalled();
      mockKeyvRedisInstance.client.isReady = true;
      await expect(
        redis.eval("online", { keys: [], arguments: [] }),
      ).resolves.toBe("value");
      await closeRedisCache();
      expect(mockKeyvRedisInstance.disconnect).toHaveBeenCalledWith(true);
      expect(getRedisClient()).toBeNull();
    });

    it("clears a deadline and releases its slot when a command throws synchronously", async () => {
      jest.useFakeTimers();
      await createRedisCache("redis://localhost:6379");
      mockKeyvRedisInstance.client.eval.mockImplementationOnce(() => {
        throw new Error("synchronous driver failure");
      });
      await expect(
        getRedisClient()!.eval("failure", { keys: [], arguments: [] }),
      ).rejects.toThrow("synchronous driver failure");
      expect(jest.getTimerCount()).toBe(0);
      await expect(
        getRedisClient()!.eval("next", { keys: [], arguments: [] }),
      ).resolves.toBe("value");
    });
  });

  describe("closeRedisCache", () => {
    it("should do nothing when no cache is initialized", async () => {
      await expect(closeRedisCache()).resolves.not.toThrow();
    });

    it("should disconnect and reset state when cache is initialized", async () => {
      await createRedisCache("redis://localhost:6379");

      await closeRedisCache();

      expect(mockKeyvRedisInstance.disconnect).toHaveBeenCalled();
    });

    it("should allow creating a new cache after closing", async () => {
      await createRedisCache("redis://localhost:6379");
      await closeRedisCache();

      // Reset mock call counts
      jest.clearAllMocks();
      mockLock.acquire = jest
        .fn()
        .mockImplementation((_key: string, fn: () => Promise<unknown>) => fn());
      mockCacheInstance.get.mockResolvedValue("ok");

      const cache = await createRedisCache("redis://localhost:6379");

      expect(cache).toBeDefined();
      expect(mockCreateCache).toHaveBeenCalledTimes(1);
    });
  });
});
