import {
  fakeRedisAdmission as mockFakeRedisAdmission,
  fakeRedisAdmissionState,
} from "@/foundation/redis/__tests__/fake-redis-counter";
import { enforcePasswordRequestLimits } from "../password-request-limits";
import { RateLimitedError, ServiceUnavailableError } from "@/shared/errors";

jest.mock("@/foundation/redis/redis-admission", () => mockFakeRedisAdmission);
let now: number;
beforeEach(() => {
  fakeRedisAdmissionState.reset();
  now = 1_000_000;
  jest.spyOn(Date, "now").mockImplementation(() => now);
});
afterEach(() => jest.restoreAllMocks());

test("a source cannot multiply its allowance by rotating target accounts", async () => {
  for (let i = 0; i < 60; i++)
    await enforcePasswordRequestLimits(`person${i}@example.com`, "192.0.2.1");
  await expect(
    enforcePasswordRequestLimits("another@example.com", "192.0.2.1"),
  ).rejects.toBeInstanceOf(RateLimitedError);
  await expect(
    enforcePasswordRequestLimits("another@example.com", "192.0.2.2"),
  ).resolves.toBeUndefined();
});

test("rotating addresses cannot multiply one account's allowance", async () => {
  for (let i = 0; i < 30; i++)
    await enforcePasswordRequestLimits("person@example.com", `192.0.2.${i}`);
  await expect(
    enforcePasswordRequestLimits(" PERSON@example.com ", "192.0.2.100"),
  ).rejects.toBeInstanceOf(RateLimitedError);
});

test("a pair has its own smaller allowance without exhausting independent users", async () => {
  for (let i = 0; i < 10; i++)
    await enforcePasswordRequestLimits("person@example.com", "192.0.2.1");
  await expect(
    enforcePasswordRequestLimits("person@example.com", "192.0.2.1"),
  ).rejects.toBeInstanceOf(RateLimitedError);
  await expect(
    enforcePasswordRequestLimits("person@example.com", "192.0.2.2"),
  ).resolves.toBeUndefined();
  await expect(
    enforcePasswordRequestLimits("other@example.com", "192.0.2.1"),
  ).resolves.toBeUndefined();
});

test("the rolling minute expires without extending on a refusal", async () => {
  for (let i = 0; i < 10; i++)
    await enforcePasswordRequestLimits("person@example.com", "192.0.2.1");
  now += 59_000;
  await expect(
    enforcePasswordRequestLimits("person@example.com", "192.0.2.1"),
  ).rejects.toMatchObject({ metadata: { retryAfter: 1 } });
  now += 1_000;
  await expect(
    enforcePasswordRequestLimits("person@example.com", "192.0.2.1"),
  ).resolves.toBeUndefined();
});

test("an hour cap survives repeated minute refills for sources and accounts", async () => {
  for (let batch = 0; batch < 5; batch++) {
    for (let i = 0; i < 60; i++)
      await enforcePasswordRequestLimits(
        `p${batch}-${i}@example.com`,
        "192.0.2.1",
      );
    now += 60_001;
  }
  await expect(
    enforcePasswordRequestLimits("next@example.com", "192.0.2.1"),
  ).rejects.toBeInstanceOf(RateLimitedError);
  fakeRedisAdmissionState.reset();
  for (let batch = 0; batch < 4; batch++) {
    for (let i = 0; i < 30; i++)
      await enforcePasswordRequestLimits("person@example.com", `192.0.2.${i}`);
    now += 60_001;
  }
  await expect(
    enforcePasswordRequestLimits("person@example.com", "192.0.2.100"),
  ).rejects.toBeInstanceOf(RateLimitedError);
});

test("unavailable shared state never admits a new password proof", async () => {
  fakeRedisAdmissionState.down = true;
  await expect(
    enforcePasswordRequestLimits("person@example.com", "192.0.2.1"),
  ).rejects.toBeInstanceOf(ServiceUnavailableError);
});
