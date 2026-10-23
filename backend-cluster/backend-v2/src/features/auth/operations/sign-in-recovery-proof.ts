import { createHash, createHmac } from "node:crypto";
import { getRedisClient } from "@/foundation/redis/redis-utils";
import { CACHE_KEYS, TTL } from "@/shared/cache";
import { ServiceUnavailableError } from "@/shared/errors";

const ISSUE = `
if redis.call('EXISTS', KEYS[2]) == 1 then return 0 end
local existing = redis.call('GET', KEYS[1])
if existing then
  if existing == ARGV[1] then return 1 else return 0 end
end
redis.call('SET', KEYS[1], ARGV[1], 'PX', ARGV[2])
return 1
`;
const CONSUME = `
local value = redis.call('GET', KEYS[1])
if not value then return '' end
local proof = cjson.decode(value)
if proof.account ~= ARGV[1] or proof.code ~= ARGV[2] then return '' end
local ttl = redis.call('PTTL', KEYS[1])
if ttl <= 0 then return '' end
redis.call('SET', KEYS[2], 'spent', 'PX', ttl)
redis.call('DEL', KEYS[1])
return proof.userId
`;

function digest(value: string): string {
  return createHash("sha256").update(value).digest("hex");
}
function keys(challengeId: string): string[] {
  const subject = digest(challengeId);
  return [
    CACHE_KEYS.auth.signInRecoveryProof(subject),
    CACHE_KEYS.auth.signInRecoverySpent(subject),
  ];
}
function mac(secret: string, label: string, value: string): string {
  if (!secret) throw new ServiceUnavailableError("Authentication", 5);
  return createHmac("sha256", secret)
    .update(`sign-in-recovery-v1:${label}\0${value}`)
    .digest("hex");
}
function codeDigest(email: string, code: string, secret: string): string {
  return mac(secret, "proof", `${email.trim().toLowerCase()}\0${code}`);
}
async function evaluate(
  script: string,
  challengeId: string,
  args: string[],
): Promise<unknown> {
  const redis = getRedisClient();
  if (!redis) throw new ServiceUnavailableError("Authentication", 5);
  try {
    return await redis.eval(script, {
      keys: keys(challengeId),
      arguments: args,
    });
  } catch {
    // Redis errors can contain proof arguments. Do not attach the original error.
    throw new ServiceUnavailableError("Authentication", 5);
  }
}

/** A retry reuses its original code and expiry. A consumed job cannot recreate it. */
export async function issueSignInRecoveryProof(
  email: string,
  userId: string,
  jobId: string,
  secret: string,
): Promise<{ code: string; challengeId: string } | null> {
  // The requester receives only the outbox receipt. Reveal the actual proof
  // challenge only in mail, so that requester cannot burn its OTP attempts.
  const challengeId = `rcv_${mac(secret, "challenge", jobId)}`;
  const code = (
    Number.parseInt(mac(secret, "code", jobId).slice(0, 12), 16) % 1_000_000
  )
    .toString()
    .padStart(6, "0");
  const record = JSON.stringify({
    account: digest(email.trim().toLowerCase()),
    code: codeDigest(email, code, secret),
    userId,
  });
  const issued = await evaluate(ISSUE, challengeId, [
    record,
    String(TTL.MIN_10),
  ]);
  if (issued !== 0 && issued !== 1)
    throw new ServiceUnavailableError("Authentication", 5);
  return issued === 1 ? { code, challengeId } : null;
}

/** Mailbox ownership is a one-use permission for one password comparison. */
export async function consumeSignInRecoveryProof(
  email: string,
  challengeId: string,
  code: string,
  secret: string,
): Promise<string | null> {
  const result = await evaluate(CONSUME, challengeId, [
    digest(email.trim().toLowerCase()),
    codeDigest(email, code, secret),
  ]);
  if (typeof result !== "string")
    throw new ServiceUnavailableError("Authentication", 5);
  return result || null;
}
