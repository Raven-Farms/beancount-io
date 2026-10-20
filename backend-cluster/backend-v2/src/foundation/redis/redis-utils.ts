import Keyv from "keyv";
import KeyvRedis from "@keyv/redis";
import { createCache, type Cache } from "cache-manager";
import { lock, LOCK_KEYS } from "@/shared/lock";
import { serialize, deserialize } from "./cache-codec";

let cacheInstance: Cache | null = null;
let keyvRedisStore: KeyvRedis<unknown> | null = null;
let boundedClient: RedisCommands | null = null;

// The driver's command timeout ends when a command is written, not when its
// reply arrives. Bound both callers' wait and the underlying retained work.
const COMMAND_TIMEOUT_MS = 1000;
const MAX_PENDING_COMMANDS = 128;
type RedisCommands = {
  incr(key: string): Promise<number>;
  pExpire(key: string, ms: number): Promise<unknown>;
  pTTL(key: string): Promise<number>;
  get(key: string): Promise<string | null>;
  del(key: string): Promise<number>;
  eval(
    script: string,
    options: { keys: string[]; arguments: string[] },
  ): Promise<unknown>;
};

function boundCommands(
  client: RedisCommands & { isReady: boolean },
): RedisCommands {
  let pending = 0;
  function run<T>(command: () => Promise<T>): Promise<T> {
    if (!client.isReady)
      return Promise.reject(new Error("Redis connection unavailable"));
    if (pending >= MAX_PENDING_COMMANDS)
      return Promise.reject(new Error("Redis command capacity exhausted"));
    pending++;
    return new Promise<T>((resolve, reject) => {
      const timer = setTimeout(
        () => reject(new Error("Redis command timed out")),
        COMMAND_TIMEOUT_MS,
      );
      // A caller timing out does not cancel a written command. Keep its slot
      // until Redis replies or the socket closes; handle late rejection too.
      const settled = () => {
        pending--;
        clearTimeout(timer);
      };
      try {
        void command().then(
          (value) => {
            settled();
            resolve(value);
          },
          (error: unknown) => {
            settled();
            reject(error);
          },
        );
      } catch (error) {
        settled();
        reject(error);
      }
    });
  }
  return {
    incr: (key) => run(() => client.incr(key)),
    pExpire: (key, ms) => run(() => client.pExpire(key, ms)),
    pTTL: (key) => run(() => client.pTTL(key)),
    get: (key) => run(() => client.get(key)),
    del: (key) => run(() => client.del(key)),
    eval: (script, options) => run(() => client.eval(script, options)),
  };
}

/**
 * Creates and validates a Redis cache connection.
 * Uses singleton pattern - returns existing cache if already created.
 * Thread-safe: uses async-lock to prevent race conditions during concurrent initialization.
 *
 * @param redisUri - Redis connection URI
 * @param namespace - Optional namespace for the cache (default: "models")
 * @returns Cache instance backed by Redis
 * @throws Error if connection validation fails or the initialization lock times out
 */
export async function createRedisCache(
  redisUri: string,
  namespace = "backend-v2",
): Promise<Cache> {
  if (!redisUri) {
    throw new Error("Redis URI required: ensure 'config.redis.uri' is set");
  }

  // Return existing instance if already initialized
  if (cacheInstance) {
    return cacheInstance;
  }

  // Use lock to prevent concurrent initialization
  return lock.acquire(LOCK_KEYS.INFRA.INIT_REDIS, async () => {
    // Double-check after acquiring lock
    if (cacheInstance) {
      return cacheInstance;
    }

    // Create Redis store and Keyv instance
    keyvRedisStore = new KeyvRedis(
      {
        url: redisUri,
        disableOfflineQueue: true,
        commandsQueueMaxLength: 256,
        commandOptions: { timeout: COMMAND_TIMEOUT_MS },
        socket: {
          connectTimeout: 2000,
          socketTimeout: 2000,
          // The driver otherwise permanently stops on socket timeouts.
          reconnectStrategy: (attempt: number) =>
            Math.min(100 * (attempt + 1), 2000),
        },
        // Prevent healthy idle connections hitting the socket inactivity timeout.
        // A stalled heartbeat stops scheduling until its pending reply settles.
        pingInterval: COMMAND_TIMEOUT_MS,
      },
      { throwOnErrors: true, connectionTimeout: 2000 },
    );
    boundedClient = boundCommands(keyvRedisStore.client as never);
    const keyvStore = new Keyv({
      store: keyvRedisStore,
      namespace,
      throwOnErrors: true,
      // Preserve Date/Map/Set/BigInt across the Redis round-trip (see cache-codec).
      serialize,
      deserialize,
    });
    cacheInstance = createCache({ stores: [keyvStore] });

    // Validate connection with a simple operation
    try {
      const testKey = "__connection_test__";
      const testValue = "ok";

      await cacheInstance.set(testKey, testValue, 1000); // 1 second TTL
      const result = await cacheInstance.get(testKey);

      if (result !== testValue) {
        throw new Error("Redis connection test failed: value mismatch");
      }

      // Clean up test key
      await cacheInstance.del(testKey);
    } catch {
      // Clean up on validation failure
      await closeRedisCache();

      throw new Error("Redis connection validation failed");
    }

    return cacheInstance;
  });
}

/**
 * The raw Redis client behind the cache, or `null` before the cache is created.
 *
 * Almost nothing should want this — the cache helper is the interface for
 * storing values. It exists for the operations Keyv cannot express because they
 * must be atomic across instances (counters and admission scripts). Callers
 * decide whether Redis unavailability may fail open; authentication admission
 * must fail closed.
 */
export function getRedisClient(): RedisCommands | null {
  return boundedClient;
}

/**
 * Closes the Redis cache connection and cleans up resources
 */
export async function closeRedisCache(): Promise<void> {
  const store = keyvRedisStore;
  keyvRedisStore = null;
  boundedClient = null;
  cacheInstance = null;
  // Closing a paused connection gracefully would wait for those same replies.
  // Destroy it so retained commands settle and shutdown cannot hang.
  if (store) await store.disconnect(true);
}
