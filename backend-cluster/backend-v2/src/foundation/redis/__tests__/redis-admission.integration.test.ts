import { spawn, type ChildProcess } from "node:child_process";
import { once } from "node:events";
import { mkdir, mkdtemp, rm } from "node:fs/promises";
import path from "node:path";
import { createClient } from "@keyv/redis";
import { getRedisClient } from "../redis-utils";
import {
  clearFailureBudget,
  completeFailureBudget,
  consumeSlidingWindows,
  reserveFailureBudget,
} from "../redis-admission";

jest.mock("../redis-utils", () => ({ getRedisClient: jest.fn() }));
jest.mock("@/shared/logger", () => ({
  logger: { child: () => ({ error: jest.fn() }) },
}));

// Starts one isolated Redis process, with persistence and TCP disabled. Run via
// yarn test:integration --runInBand redis-admission (requires redis-server).
let server: ChildProcess;
let scratch: string;
let client: ReturnType<typeof createClient>;

beforeAll(async () => {
  const tmp = path.join(process.cwd(), "tmp");
  await mkdir(tmp, { recursive: true });
  scratch = await mkdtemp(path.join(tmp, "redis-admission-"));
  // Relative socket names stay below Unix path limits in deep checkouts.
  const socket = path.relative(process.cwd(), path.join(scratch, "redis.sock"));
  server = spawn(
    "redis-server",
    [
      "--port",
      "0",
      "--unixsocket",
      "redis.sock",
      "--save",
      "",
      "--appendonly",
      "no",
      "--dir",
      scratch,
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
    server.once("exit", (code) => {
      clearTimeout(timeout);
      reject(new Error(`Isolated Redis exited (${code})`));
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
  jest.mocked(getRedisClient).mockReturnValue(client);
});

beforeEach(async () => {
  await client.flushDb();
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

async function serverNow(): Promise<number> {
  return Number(
    await client.eval(
      "local t = redis.call('TIME'); return t[1]*1000 + math.floor(t[2]/1000)",
      { keys: [], arguments: [] },
    ),
  );
}

async function reserve(
  key = "account",
  max = 10,
  windowMs = 60_000,
): Promise<string> {
  const result = await reserveFailureBudget(key, max, windowMs);
  expect(result?.allowed).toBe(true);
  expect(result?.reservationId).toEqual(expect.any(String));
  return result!.reservationId!;
}

it("admits exactly the shared limit under parallel rolling-window requests", async () => {
  const buckets = [
    { key: "ip", max: 10, windowMs: 60_000 },
    { key: "email", max: 20, windowMs: 60_000 },
  ];
  const results = await Promise.all(
    Array.from({ length: 25 }, () => consumeSlidingWindows(buckets)),
  );

  expect(results.filter((result) => result?.allowed)).toHaveLength(10);
  expect(results.filter((result) => !result?.allowed)).toHaveLength(15);
  expect(await client.zCard("ip")).toBe(10);
  expect(await client.zCard("email")).toBe(10);
  expect(
    results
      .filter((result) => !result?.allowed)
      .every((result) => result!.retryAfterMs > 0),
  ).toBe(true);
});

it("consumes no other bucket when any dimension rejects, and rejection does not extend expiry", async () => {
  await consumeSlidingWindows([{ key: "blocked", max: 1, windowMs: 60_000 }]);
  const before = await client.pTTL("blocked");
  await new Promise((resolve) => setTimeout(resolve, 30));

  const result = await consumeSlidingWindows([
    { key: "free", max: 5, windowMs: 60_000 },
    { key: "blocked", max: 1, windowMs: 60_000 },
  ]);

  expect(result?.allowed).toBe(false);
  expect(await client.exists("free")).toBe(0);
  expect(await client.pTTL("blocked")).toBeLessThanOrEqual(before - 20);
});

it("expires individual events in a rolling window rather than resetting a whole fixed window", async () => {
  const now = await serverNow();
  await client.zAdd("window", [
    { score: now - 60_001, value: "expired" },
    { score: now - 30_000, value: "live" },
  ]);

  expect(
    (await consumeSlidingWindows([{ key: "window", max: 2, windowMs: 60_000 }]))
      ?.allowed,
  ).toBe(true);
  const rejection = await consumeSlidingWindows([
    { key: "window", max: 2, windowMs: 60_000 },
  ]);

  expect(await client.zScore("window", "expired")).toBeNull();
  expect(await client.zCard("window")).toBe(2);
  expect(rejection?.allowed).toBe(false);
  expect(rejection?.retryAfterMs).toBeGreaterThan(29_000);
  expect(rejection?.retryAfterMs).toBeLessThanOrEqual(30_000);
});

it("uses Redis time for admission even when a backend instance has an incorrect clock", async () => {
  const clock = jest.spyOn(Date, "now").mockReturnValue(0);
  try {
    const reservation = await reserve();
    expect(await client.zScore("account:pending", reservation)).toBeGreaterThan(
      await serverNow(),
    );
    await consumeSlidingWindows([{ key: "ip", max: 1, windowMs: 60_000 }]);
    expect(
      Number((await client.zRangeWithScores("ip", 0, 0))[0].score),
    ).toBeGreaterThan(1_000_000_000_000);
  } finally {
    clock.mockRestore();
  }
});

it("reserves only ten password verifiers among 25 concurrent requests, retaining failures", async () => {
  const results = await Promise.all(
    Array.from({ length: 25 }, () =>
      reserveFailureBudget("account", 10, 60_000),
    ),
  );
  const admitted = results.filter((result) => result?.allowed);
  expect(admitted).toHaveLength(10);
  expect(new Set(admitted.map((result) => result!.reservationId)).size).toBe(
    10,
  );
  expect(await client.zCard("account:pending")).toBe(10);

  await Promise.all(
    admitted.map((result) =>
      completeFailureBudget(
        "account",
        60_000,
        result!.reservationId!,
        "failure",
      ),
    ),
  );

  expect(await client.zCard("account:pending")).toBe(0);
  expect(await client.zCard("account:failures")).toBe(10);
  expect((await reserveFailureBudget("account", 10, 60_000))?.allowed).toBe(
    false,
  );
});

it("a successful verifier clears failures but preserves other live reservations", async () => {
  const failed = await reserve("account", 3);
  const success = await reserve("account", 3);
  const other = await reserve("account", 3);
  await completeFailureBudget("account", 60_000, failed, "failure");
  expect((await reserveFailureBudget("account", 3, 60_000))?.allowed).toBe(
    false,
  );

  expect(
    await completeFailureBudget("account", 60_000, success, "success"),
  ).toBe(true);

  expect(await client.zCard("account:failures")).toBe(0);
  expect(await client.zScore("account:pending", other)).not.toBeNull();
  await reserve("account", 3);
  await reserve("account", 3);
  expect((await reserveFailureBudget("account", 3, 60_000))?.allowed).toBe(
    false,
  );
});

it("cancellation frees only its own reservation and cannot be completed twice", async () => {
  const cancelled = await reserve("account", 2);
  const other = await reserve("account", 2);

  expect(
    await completeFailureBudget("account", 60_000, cancelled, "cancel"),
  ).toBe(true);
  expect(
    await completeFailureBudget("account", 60_000, cancelled, "failure"),
  ).toBe(false);
  expect(await client.zCard("account:failures")).toBe(0);
  expect(await client.zScore("account:pending", other)).not.toBeNull();
  await reserve("account", 2);
  expect((await reserveFailureBudget("account", 2, 60_000))?.allowed).toBe(
    false,
  );
});

it("rejects expired or missing leases without clearing existing failures", async () => {
  const failed = await reserve();
  await completeFailureBudget("account", 60_000, failed, "failure");
  const expired = await reserve();
  await client.zAdd("account:pending", {
    score: (await serverNow()) - 1,
    value: expired,
  });

  expect(
    await completeFailureBudget("account", 60_000, expired, "success"),
  ).toBe(false);
  expect(
    await completeFailureBudget("account", 60_000, "absent", "failure"),
  ).toBe(false);
  expect(await client.zCard("account:failures")).toBe(1);
});

it("cleans expired failures and abandoned leases before admitting a verifier", async () => {
  const now = await serverNow();
  await client.zAdd("account:failures", {
    score: now - 1,
    value: "old-failure",
  });
  await client.zAdd("account:pending", {
    score: now - 1,
    value: "abandoned-verifier",
  });

  await reserve("account", 1);

  expect(await client.zCard("account:failures")).toBe(0);
  expect(await client.zCard("account:pending")).toBe(1);
});

it("expires individual failed attempts while retaining later failures in the same set", async () => {
  const older = await reserve("account", 2);
  await completeFailureBudget("account", 60_000, older, "failure");
  const newer = await reserve("account", 2);
  await completeFailureBudget("account", 60_000, newer, "failure");
  const newerExpiry = await client.zScore("account:failures", newer);
  expect(newerExpiry).toBeGreaterThan(await serverNow());
  // Advance only the older event beyond its rolling expiration; the Redis key
  // itself still has a live TTL due to the later failed attempt.
  await client.zAdd("account:failures", {
    score: (await serverNow()) - 1,
    value: older,
  });

  await reserve("account", 2);

  expect(await client.zScore("account:failures", older)).toBeNull();
  expect(await client.zScore("account:failures", newer)).toBe(newerExpiry);
  expect((await reserveFailureBudget("account", 2, 60_000))?.allowed).toBe(
    false,
  );
});

it("reset invalidates pending work so stale failures cannot restore the budget", async () => {
  const stale = await reserve("account", 1);
  await clearFailureBudget("account");
  const current = await reserve("account", 1);

  expect(await completeFailureBudget("account", 60_000, stale, "failure")).toBe(
    false,
  );
  expect(await completeFailureBudget("account", 60_000, stale, "success")).toBe(
    false,
  );
  expect(await client.zScore("account:pending", current)).not.toBeNull();
  expect(await client.zCard("account:failures")).toBe(0);
});

it("denied failure-budget requests do not renew either lease or failure expiration", async () => {
  const failed = await reserve("account", 2);
  await completeFailureBudget("account", 60_000, failed, "failure");
  await reserve("account", 2);
  const failureTtl = await client.pTTL("account:failures");
  const pendingTtl = await client.pTTL("account:pending");
  await new Promise((resolve) => setTimeout(resolve, 30));

  const result = await reserveFailureBudget("account", 2, 60_000);

  expect(result?.allowed).toBe(false);
  expect(result?.retryAfterMs).toBeLessThanOrEqual(30_000);
  expect(result?.retryAfterMs).toBeGreaterThan(29_000);
  expect(await client.pTTL("account:failures")).toBeLessThanOrEqual(
    failureTtl - 20,
  );
  expect(await client.pTTL("account:pending")).toBeLessThanOrEqual(
    pendingTtl - 20,
  );
});
