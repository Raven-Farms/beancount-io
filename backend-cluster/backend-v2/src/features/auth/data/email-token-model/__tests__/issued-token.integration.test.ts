import { spawn, type ChildProcess } from "node:child_process";
import { once } from "node:events";
import { mkdir, mkdtemp, rm } from "node:fs/promises";
import path from "node:path";
import { createClient } from "@keyv/redis";
import type { Cache } from "cache-manager";
import { getRedisClient } from "@/foundation/redis/redis-utils";
import { CACHE_KEYS } from "@/shared/cache";
import { ServiceUnavailableError } from "@/shared/errors";
import { EmailTokenRedisModel } from "../redis-impl";

jest.mock("@/foundation/redis/redis-utils", () => ({
  getRedisClient: jest.fn(),
}));

let server: ChildProcess;
let scratch: string;
let client: ReturnType<typeof createClient>;
let model: EmailTokenRedisModel;
const legacy = new Map<string, string>();

beforeAll(async () => {
  await mkdir(path.join(process.cwd(), "tmp"), { recursive: true });
  scratch = await mkdtemp(path.join(process.cwd(), "tmp", "issued-token-"));
  const socket = path.relative(process.cwd(), path.join(scratch, "r.sock"));
  server = spawn(
    "redis-server",
    [
      "--port",
      "0",
      "--unixsocket",
      "r.sock",
      "--save",
      "",
      "--appendonly",
      "no",
    ],
    { cwd: scratch, stdio: ["ignore", "pipe", "pipe"] },
  );
  await new Promise<void>((resolve, reject) => {
    let output = "";
    const timeout = setTimeout(
      () => reject(new Error("Isolated Redis startup timed out")),
      5000,
    );
    server.once("error", (error) => {
      clearTimeout(timeout);
      reject(error);
    });
    server.once("exit", () => {
      clearTimeout(timeout);
      reject(new Error("Isolated Redis exited"));
    });
    server.stdout!.on("data", (chunk: Buffer) => {
      output += chunk.toString();
      if (output.toLowerCase().includes("ready to accept connections")) {
        clearTimeout(timeout);
        resolve();
      }
    });
  });
  client = createClient({ socket: { path: socket, reconnectStrategy: false } });
  await client.connect();
});

beforeEach(async () => {
  jest.mocked(getRedisClient).mockReturnValue(client);
  await client.flushDb();
  legacy.clear();
  model = new EmailTokenRedisModel({
    cache: {
      get: async (key: string) => legacy.get(key),
      set: async (key: string, value: string) => {
        legacy.set(key, value);
      },
      del: async (key: string) => {
        legacy.delete(key);
      },
    } as unknown as Cache,
    expMins: 5,
  });
});

afterAll(async () => {
  if (client?.isOpen) await client.quit();
  if (server?.pid && server.exitCode === null) {
    const exited = once(server, "exit");
    server.kill();
    await exited;
  }
  if (scratch) await rm(scratch, { recursive: true, force: true });
});

it("issues idempotently across concurrent workers, preserving earlier reset links and original expiry", async () => {
  const expires = new Date(Date.now() + 60_000);
  const first = await model.issueToken("user_test", "earlier-token", expires);
  const results = await Promise.all(
    Array.from({ length: 25 }, () =>
      model.issueToken("user_test", "job-token", expires),
    ),
  );
  expect(results.every((record) => record?.token === "job-token")).toBe(true);
  expect(await model.findOne("earlier-token")).toEqual(first);
  const retry = await model.issueToken(
    "user_test",
    "job-token",
    new Date(Date.now() + 300_000),
  );
  expect(retry?.expireAt).toBe(expires.toISOString());
  expect(await model.issueToken("other-user", "job-token", expires)).toBeNull();
});

it("consumes a reset token once under concurrency and refuses resurrection on a delivery retry", async () => {
  const expires = new Date(Date.now() + 60_000);
  await model.issueToken("user_test", "one-use-token", expires);
  const results = await Promise.all(
    Array.from({ length: 25 }, () => model.findOneAndDelete("one-use-token")),
  );
  expect(results.filter(Boolean)).toHaveLength(1);
  expect(await model.findOne("one-use-token")).toBeNull();
  expect(
    await model.issueToken("user_test", "one-use-token", expires),
  ).toBeNull();
  expect(
    await model.issueToken(
      "user_test",
      "already-expired",
      new Date(Date.now() - 1),
    ),
  ).toBeNull();
});

it("revokes every issued token for one user and keeps tombstones and other users' links", async () => {
  const expires = new Date(Date.now() + 60_000);
  await model.issueToken("user_test", "first-token", expires);
  await model.issueToken("user_test", "second-token", expires);
  await model.issueToken("other-user", "other-token", expires);

  await model.deleteByUserId("user_test");

  expect(await model.findOne("first-token")).toBeNull();
  expect(await model.findOne("second-token")).toBeNull();
  expect(
    await model.issueToken("user_test", "first-token", expires),
  ).toBeNull();
  expect((await model.findOne("other-token"))?.userId).toBe("other-user");
});

it("keeps legacy cache-backed tokens readable and consumable alongside new tokens", async () => {
  const record = {
    userId: "user_test",
    token: "legacy-token",
    expireAt: new Date(Date.now() + 60_000).toISOString(),
  };
  legacy.set(
    CACHE_KEYS.auth.emailTokenByToken(record.token),
    JSON.stringify(record),
  );
  legacy.set(
    CACHE_KEYS.auth.emailTokensByUser(record.userId),
    JSON.stringify([record.token]),
  );
  await model.issueToken(
    "user_test",
    "new-token",
    new Date(Date.now() + 60_000),
  );

  expect(await model.findOne(record.token)).toEqual(record);
  expect(await model.findOneAndDelete(record.token)).toEqual(record);
  expect(await model.findOne(record.token)).toBeNull();
  expect((await model.findOne("new-token"))?.token).toBe("new-token");
});

it("atomically claims legacy redemption even when concurrent readers already fetched its record", async () => {
  const record = {
    userId: "user_test",
    token: "legacy-concurrent",
    expireAt: new Date(Date.now() + 60_000).toISOString(),
  };
  legacy.set(
    CACHE_KEYS.auth.emailTokenByToken(record.token),
    JSON.stringify(record),
  );
  legacy.set(
    CACHE_KEYS.auth.emailTokensByUser(record.userId),
    JSON.stringify([record.token]),
  );
  const results = await Promise.all(
    Array.from({ length: 25 }, () => model.findOneAndDelete(record.token)),
  );
  expect(results.filter(Boolean)).toHaveLength(1);
  expect(await model.findOne(record.token)).toBeNull();
});

it("fails closed on Redis outage without exposing driver command values", async () => {
  jest.mocked(getRedisClient).mockReturnValue({
    eval: async () => {
      throw new Error("secret-token private@email.example");
    },
  } as never);
  for (const operation of [
    model.issueToken("user_test", "secret-token"),
    model.findOne("secret-token"),
    model.findOneAndDelete("secret-token"),
  ]) {
    await expect(operation).rejects.toBeInstanceOf(ServiceUnavailableError);
    await expect(operation).rejects.not.toThrow("secret-token");
  }
});
