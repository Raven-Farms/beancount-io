import {
  fakeRedisAdmission as mockAdmission,
  fakeRedisAdmissionState,
} from "@/foundation/redis/__tests__/fake-redis-counter";
import {
  consumeMailDelivery,
  enforceMailRequestLimits,
  enforceRecoveryProofLimits,
  enforceVerifiedRecoveryAccountLimit,
} from "../auth-mail-limits";
import { RateLimitedError, ServiceUnavailableError } from "@/shared/errors";
jest.mock("@/foundation/redis/redis-admission", () => mockAdmission);
let now: number;
beforeEach(() => {
  fakeRedisAdmissionState.reset();
  now = 1_000_000;
  jest.spyOn(Date, "now").mockImplementation(() => now);
});
afterEach(() => jest.restoreAllMocks());

test("all mail actions share cooldown and rolling hourly delivery cap", async () => {
  for (let n = 0; n < 5; n++) {
    expect(await consumeMailDelivery("person@example.com")).toBe(true);
    expect(await consumeMailDelivery(" PERSON@example.com ")).toBe(false);
    now += 60_000;
  }
  expect(await consumeMailDelivery("person@example.com")).toBe(false);
  expect(await consumeMailDelivery("other@example.com")).toBe(true);
  now = 4_600_000;
  expect(await consumeMailDelivery("person@example.com")).toBe(true);
});

test("mail request volume is charged before controlled account key allocation", async () => {
  for (let n = 0; n < 10; n++)
    await enforceMailRequestLimits(`p${n}@example.com`, "192.0.2.1");
  await expect(
    enforceMailRequestLimits("new@example.com", "192.0.2.1"),
  ).rejects.toBeInstanceOf(RateLimitedError);
  await expect(
    enforceMailRequestLimits("new@example.com", "192.0.2.2"),
  ).resolves.toBeUndefined();
  expect(
    [...fakeRedisAdmissionState.windows.keys()].some((k) => k.includes("@")),
  ).toBe(false);
});

test("OTP challenge attempts cannot be multiplied by rotating source addresses", async () => {
  for (let n = 0; n < 5; n++)
    await enforceRecoveryProofLimits("challenge-a", `192.0.2.${n}`);
  await expect(
    enforceRecoveryProofLimits("challenge-a", "192.0.2.99"),
  ).rejects.toBeInstanceOf(RateLimitedError);
  await expect(
    enforceRecoveryProofLimits("challenge-b", "192.0.2.99"),
  ).resolves.toBeUndefined();
});

test("all mail and proof admission fail closed on unavailable shared state", async () => {
  fakeRedisAdmissionState.down = true;
  await expect(consumeMailDelivery("p@example.com")).rejects.toBeInstanceOf(
    ServiceUnavailableError,
  );
  await expect(
    enforceMailRequestLimits("p@example.com", "192.0.2.1"),
  ).rejects.toBeInstanceOf(ServiceUnavailableError);
  await expect(
    enforceRecoveryProofLimits("challenge", "192.0.2.1"),
  ).rejects.toBeInstanceOf(ServiceUnavailableError);
  await expect(
    enforceVerifiedRecoveryAccountLimit("p@example.com"),
  ).rejects.toBeInstanceOf(ServiceUnavailableError);
});

test("verified-account allowance is normalized, independent and rolls over after fifteen minutes", async () => {
  for (let n = 0; n < 3; n++) {
    await enforceVerifiedRecoveryAccountLimit(
      n % 2 ? " PERSON@example.com " : "person@example.com",
    );
  }
  await expect(
    enforceVerifiedRecoveryAccountLimit("person@example.com"),
  ).rejects.toBeInstanceOf(RateLimitedError);
  await expect(
    enforceVerifiedRecoveryAccountLimit("other@example.com"),
  ).resolves.toBeUndefined();
  now += 15 * 60_000;
  await expect(
    enforceVerifiedRecoveryAccountLimit("person@example.com"),
  ).resolves.toBeUndefined();
});
