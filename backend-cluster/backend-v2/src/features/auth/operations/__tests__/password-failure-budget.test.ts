import {
  fakeRedisAdmission as mockFakeRedisAdmission,
  fakeRedisAdmissionState,
} from "@/foundation/redis/__tests__/fake-redis-counter";
import {
  clearPasswordFailures,
  verifyPasswordWithinBudget,
} from "../password-failure-budget";
import { RateLimitedError, ServiceUnavailableError } from "@/shared/errors";

jest.mock("@/foundation/redis/redis-admission", () => mockFakeRedisAdmission);
beforeEach(() => fakeRedisAdmissionState.reset());
afterEach(() => jest.restoreAllMocks());

function deferred() {
  let resolve!: (result: boolean) => void;
  const promise = new Promise<boolean>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

test("25 simultaneous failures admit exactly ten verifications", async () => {
  const gate = deferred();
  const verify = jest.fn(() => gate.promise);
  const attempts = Array.from({ length: 25 }, () =>
    verifyPasswordWithinBudget("person@example.com", verify),
  );
  const settled = Promise.allSettled(attempts);
  await Promise.resolve();
  expect(verify).toHaveBeenCalledTimes(10);
  gate.resolve(false);
  const results = await settled;
  expect(results.filter((r) => r.status === "fulfilled")).toHaveLength(10);
  expect(
    results.filter(
      (r) => r.status === "rejected" && r.reason instanceof RateLimitedError,
    ),
  ).toHaveLength(15);
  await expect(
    verifyPasswordWithinBudget("person@example.com", async () => true),
  ).rejects.toBeInstanceOf(RateLimitedError);
});

test("a success leaves other in-flight reservations in place", async () => {
  const gate = deferred();
  const attempts = Array.from({ length: 9 }, () =>
    verifyPasswordWithinBudget("person@example.com", () => gate.promise),
  );
  await expect(
    verifyPasswordWithinBudget("person@example.com", async () => true),
  ).resolves.toBe(true);
  const last = verifyPasswordWithinBudget(
    "person@example.com",
    () => gate.promise,
  );
  await expect(
    verifyPasswordWithinBudget("person@example.com", async () => false),
  ).rejects.toBeInstanceOf(RateLimitedError);
  gate.resolve(false);
  await Promise.all([...attempts, last]);
});

test("a reset invalidates older in-flight attempts without poisoning the next window", async () => {
  const gate = deferred();
  const attempt = verifyPasswordWithinBudget(
    "person@example.com",
    () => gate.promise,
  );
  await Promise.resolve();
  await clearPasswordFailures("PERSON@example.com");
  gate.resolve(false);
  await expect(attempt).rejects.toBeInstanceOf(ServiceUnavailableError);
  await expect(
    verifyPasswordWithinBudget("person@example.com", async () => true),
  ).resolves.toBe(true);
});

test("a verifier failure cancels its reservation", async () => {
  const error = new Error("database unavailable");
  await expect(
    verifyPasswordWithinBudget("person@example.com", async () => {
      throw error;
    }),
  ).rejects.toBe(error);
  for (let i = 0; i < 10; i++)
    await expect(
      verifyPasswordWithinBudget("person@example.com", async () => false),
    ).resolves.toBe(false);
});

test("a lost or expired lease cannot authorize a successful password proof", async () => {
  let now = 1_000_000;
  jest.spyOn(Date, "now").mockImplementation(() => now);
  const gate = deferred();
  const attempt = verifyPasswordWithinBudget(
    "person@example.com",
    () => gate.promise,
  );
  await Promise.resolve();
  now += 30_001;
  gate.resolve(true);
  await expect(attempt).rejects.toBeInstanceOf(ServiceUnavailableError);
});

test("Redis failures reject before verification and during settlement", async () => {
  fakeRedisAdmissionState.down = true;
  const verify = jest.fn(async () => true);
  await expect(
    verifyPasswordWithinBudget("person@example.com", verify),
  ).rejects.toBeInstanceOf(ServiceUnavailableError);
  expect(verify).not.toHaveBeenCalled();
  fakeRedisAdmissionState.down = false;
  await expect(
    verifyPasswordWithinBudget("person@example.com", async () => {
      fakeRedisAdmissionState.down = true;
      return true;
    }),
  ).rejects.toBeInstanceOf(ServiceUnavailableError);
});
