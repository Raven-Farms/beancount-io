import type { Cache } from "cache-manager";
import crypto from "crypto";
import { getRedisClient } from "@/foundation/redis/redis-utils";
import { ServiceUnavailableError } from "@/shared/errors";
import { getExpireEpochMins } from "@/shared/expire-epoch";
import { CACHE_KEYS } from "@/shared/cache";
import {
  createRedisRecordStore,
  type RedisRecordStore,
} from "@/shared/redis-record-store";
import { EmailToken, IEmailTokenModel } from "./types";

type Opts = {
  cache: Cache;
  expMins: number;
};

export class EmailTokenRedisModel implements IEmailTokenModel {
  // Strict Redis-backed store: a dropped token write must surface (not fail open).
  private store: RedisRecordStore;
  private expMins: number;

  constructor({ cache, expMins }: Opts) {
    this.store = createRedisRecordStore(cache);
    this.expMins = expMins;
  }

  public async issueToken(
    userId: string,
    token: string,
    expiresAt = new Date(getExpireEpochMins(this.expMins)),
  ): Promise<EmailToken | null> {
    const record: EmailToken = {
      userId,
      token,
      expireAt: expiresAt.toISOString(),
    };
    const result = await this.issuedCommand(
      `
      local existing = redis.call('GET', KEYS[1])
      if existing then
        local value = cjson.decode(existing)
        if value.consumed or value.userId ~= ARGV[1] then return nil end
        return existing
      end
      local t = redis.call('TIME')
      local now = t[1]*1000 + math.floor(t[2]/1000)
      local expires = tonumber(ARGV[2])
      if expires <= now then return nil end
      redis.call('SET', KEYS[1], ARGV[3], 'PX', expires-now)
      redis.call('ZADD', KEYS[2], expires, KEYS[1])
      local latest = redis.call('ZREVRANGE', KEYS[2], 0, 0, 'WITHSCORES')
      redis.call('PEXPIREAT', KEYS[2], latest[2])
      return ARGV[3]
    `,
      [this.issuedKey(token), CACHE_KEYS.auth.emailTokensIssuedByUser(userId)],
      [userId, String(expiresAt.getTime()), JSON.stringify(record)],
    );
    return typeof result === "string"
      ? (JSON.parse(result) as EmailToken)
      : null;
  }

  private issuedKey(token: string): string {
    return CACHE_KEYS.auth.emailTokenIssued(
      crypto.createHash("sha256").update(token).digest("hex"),
    );
  }

  private async issuedCommand(
    script: string,
    keys: string[],
    args: string[],
  ): Promise<unknown> {
    const client = getRedisClient();
    if (!client) throw new ServiceUnavailableError("Email token storage", 5);
    try {
      return await client.eval(script, { keys, arguments: args });
    } catch {
      // Driver errors can include command values, including the token itself.
      throw new ServiceUnavailableError("Email token storage", 5);
    }
  }

  /** undefined means a legacy token, null means an issued but consumed token. */
  private async readIssued(
    token: string,
    consume: boolean,
  ): Promise<EmailToken | null | undefined> {
    if (!getRedisClient()) return undefined;
    const result = await this.issuedCommand(
      `
      local value = redis.call('GET', KEYS[1])
      if not value then return nil end
      local data = cjson.decode(value)
      if data.consumed then return 'null' end
      if ARGV[1] == 'consume' then
        local ttl = redis.call('PTTL', KEYS[1])
        if ttl <= 0 then return 'null' end
        data.consumed = true
        redis.call('SET', KEYS[1], cjson.encode(data), 'PX', ttl)
      end
      return value
    `,
      [this.issuedKey(token)],
      [consume ? "consume" : "read"],
    );
    return typeof result === "string"
      ? (JSON.parse(result) as EmailToken | null)
      : undefined;
  }

  /**
   * Regenerate token for a user.
   * Deletes all existing tokens for the user before creating a new one.
   *
   * Key naming strategy (see CACHE_KEYS.auth):
   * - auth:email_token:token:{uuid} - Stores EmailToken JSON with TTL
   * - auth:email_token:user:{userId} - Array of token UUIDs for user
   */
  public async regenerateToken(userId: string): Promise<EmailToken> {
    // 1. Delete all existing tokens for this user
    await this.deleteByUserId(userId);

    // 2. Generate new token
    const token = crypto.randomUUID();
    const expireAt = new Date(getExpireEpochMins(this.expMins));

    // 3. Create token data
    const tokenData: EmailToken = {
      token,
      userId,
      expireAt: expireAt.toISOString(),
    };

    // 4. Store token with TTL (in milliseconds)
    const ttlMs = this.expMins * 60 * 1000;
    await this.store.putRecord(
      CACHE_KEYS.auth.emailTokenByToken(token),
      tokenData,
      ttlMs,
    );

    // 5. Store user->tokens mapping
    const userKey = CACHE_KEYS.auth.emailTokensByUser(userId);
    const tokens = (await this.store.getRecord<string[]>(userKey)) ?? [];
    tokens.push(token);
    await this.store.putRecord(userKey, tokens, ttlMs);

    return tokenData;
  }

  /**
   * Find a token and delete it atomically.
   * Returns the token data if found, null otherwise.
   */
  public async findOneAndDelete(token: string): Promise<EmailToken | null> {
    const issued = await this.readIssued(token, true);
    if (issued !== undefined) return issued;
    const tokenData = await this.store.getRecord<EmailToken>(
      CACHE_KEYS.auth.emailTokenByToken(token),
    );

    if (!tokenData) return null;

    // Legacy records live in Keyv's encoded namespace. Claim their redemption
    // in raw Redis before deleting that record; two readers cannot both reset.
    const claimed = await this.issuedCommand(
      `
      local t = redis.call('TIME')
      local now = t[1]*1000 + math.floor(t[2]/1000)
      local ttl = tonumber(ARGV[2])-now
      if ttl <= 0 then return 0 end
      local value = redis.call('SET', KEYS[1], ARGV[3], 'NX', 'PX', ttl)
      return value and 1 or 0
    `,
      [this.issuedKey(token)],
      [
        "legacy",
        String(new Date(tokenData.expireAt).getTime()),
        JSON.stringify({ ...tokenData, consumed: true }),
      ],
    );
    if (claimed !== 1) return null;

    // Delete token
    await this.store.deleteRecord(CACHE_KEYS.auth.emailTokenByToken(token));

    // Remove from user->tokens mapping
    const userKey = CACHE_KEYS.auth.emailTokensByUser(tokenData.userId);
    const existingTokens = await this.store.getRecord<string[]>(userKey);
    if (existingTokens) {
      const filtered = existingTokens.filter((t) => t !== token);
      if (filtered.length > 0) {
        const remainingTtlMs =
          new Date(tokenData.expireAt).getTime() - Date.now();
        if (remainingTtlMs > 0) {
          await this.store.putRecord(userKey, filtered, remainingTtlMs);
        } else {
          await this.store.deleteRecord(userKey);
        }
      } else {
        await this.store.deleteRecord(userKey);
      }
    }

    return tokenData;
  }

  /**
   * Find a token without deleting it.
   * Returns the token data if found, null otherwise.
   */
  public async findOne(token: string): Promise<EmailToken | null> {
    const issued = await this.readIssued(token, false);
    if (issued !== undefined) return issued;
    return this.store.getRecord<EmailToken>(
      CACHE_KEYS.auth.emailTokenByToken(token),
    );
  }

  /**
   * Delete all tokens for a user.
   */
  public async deleteByUserId(userId: string): Promise<void> {
    if (getRedisClient()) {
      await this.issuedCommand(
        `
        for _, key in ipairs(redis.call('ZRANGE', KEYS[1], 0, -1)) do
          local value = redis.call('GET', key)
          local ttl = redis.call('PTTL', key)
          if value and ttl > 0 then
            local data = cjson.decode(value)
            data.consumed = true
            redis.call('SET', key, cjson.encode(data), 'PX', ttl)
          end
        end
        return redis.call('DEL', KEYS[1])
      `,
        [CACHE_KEYS.auth.emailTokensIssuedByUser(userId)],
        [],
      );
    }
    const userKey = CACHE_KEYS.auth.emailTokensByUser(userId);
    const existingTokens = await this.store.getRecord<string[]>(userKey);

    if (!existingTokens) return;

    // Delete all token keys
    await Promise.all(
      existingTokens.map((token) =>
        this.store.deleteRecord(CACHE_KEYS.auth.emailTokenByToken(token)),
      ),
    );

    // Delete user mapping
    await this.store.deleteRecord(userKey);
  }
}
