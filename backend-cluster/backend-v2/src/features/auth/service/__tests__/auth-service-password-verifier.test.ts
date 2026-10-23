import "reflect-metadata";
import bcrypt from "bcryptjs";
import {
  fakeRedisAdmission as mockFakeRedisAdmission,
  fakeRedisAdmissionState,
} from "@/foundation/redis/__tests__/fake-redis-counter";
import * as requestLimits from "@/features/auth/operations/password-request-limits";
import { BadUserInputError, RateLimitedError } from "@/shared/errors";
import { AuthService } from "../auth-service";

jest.mock("@/foundation/redis/redis-admission", () => mockFakeRedisAdmission);

const ACCOUNT = {
  id: "usr_test",
  email: "person@example.com",
  password: "$2b$10$5mBgP06bwKPcyhp0Fg7sqeIACeCt.enWK4cu2U7FJjlUzB9as/vQS",
  isBlocked: false,
};

function fixture() {
  const user = {
    getByMail: jest.fn(async () => ({ ...ACCOUNT }) as typeof ACCOUNT | null),
    getByIdForUpdate: jest.fn(async () => ({ ...ACCOUNT })),
    verifyPassword: jest.fn(async () => true),
  };
  const jwt = {
    create: jest.fn(async () => ({ token: "token", expireAt: new Date(0) })),
  };
  const db = {
    transaction: jest.fn(async (callback: (tx: unknown) => Promise<unknown>) =>
      callback({}),
    ),
  };
  const service = new AuthService(
    { user, jwt } as never,
    db as never,
    {} as never,
    {} as never,
    {} as never,
    {} as never,
    async () => false,
  );
  return { user, jwt, db, service };
}

beforeEach(() => fakeRedisAdmissionState.reset());
afterEach(() => jest.restoreAllMocks());

it("passes normalized email and the trusted source to admission before account lookup", async () => {
  const { user, db, service } = fixture();
  const events: string[] = [];
  const admission = jest
    .spyOn(requestLimits, "enforcePasswordRequestLimits")
    .mockImplementation(async () => {
      events.push("admitted");
    });
  user.getByMail.mockImplementation(async () => {
    events.push("lookup");
    return ACCOUNT;
  });
  user.verifyPassword.mockImplementation(async () => {
    events.push("compare");
    return true;
  });

  await service.loginUser({
    email: " PERSON@EXAMPLE.COM ",
    password: "password",
    ip: "198.51.100.5",
  });

  expect(admission).toHaveBeenCalledWith(ACCOUNT.email, "198.51.100.5");
  expect(user.getByMail).toHaveBeenCalledWith(db, ACCOUNT.email);
  expect(events).toEqual(["admitted", "lookup", "compare"]);
});

it("refuses a spent request budget before DB access or bcrypt, even for correct credentials", async () => {
  const { user, jwt, service } = fixture();
  const compare = jest.spyOn(bcrypt, "compare");
  const refusal = new RateLimitedError(60);
  jest
    .spyOn(requestLimits, "enforcePasswordRequestLimits")
    .mockRejectedValue(refusal);

  await expect(
    service.loginUser({ email: ACCOUNT.email, password: "correct" }),
  ).rejects.toBe(refusal);
  expect(user.getByMail).not.toHaveBeenCalled();
  expect(user.verifyPassword).not.toHaveBeenCalled();
  expect(compare).not.toHaveBeenCalled();
  expect(jwt.create).not.toHaveBeenCalled();
});

it.each(["absent account", "account without password"])(
  "runs one cost-10 dummy comparison for %s and returns generic invalid credentials",
  async (kind) => {
    const { user, jwt, service } = fixture();
    user.getByMail.mockResolvedValue(
      kind === "absent account" ? null : { ...ACCOUNT, password: "" },
    );
    const compare = jest.spyOn(bcrypt, "compare");

    await expect(
      service.verifyPasswordCredentials(ACCOUNT.email, "wrong", "198.51.100.1"),
    ).rejects.toBeInstanceOf(BadUserInputError);

    expect(compare).toHaveBeenCalledTimes(1);
    expect(bcrypt.getRounds(compare.mock.calls[0][1] as string)).toBe(10);
    expect(user.verifyPassword).not.toHaveBeenCalled();
    expect(jwt.create).not.toHaveBeenCalled();
  },
);

it("keeps the model's real password verifier for accounts with a password", async () => {
  const { user, db, service } = fixture();
  const compare = jest.spyOn(bcrypt, "compare");

  await expect(
    service.verifyPasswordCredentials(ACCOUNT.email, "password"),
  ).resolves.toEqual(ACCOUNT);

  expect(user.verifyPassword).toHaveBeenCalledWith(db, ACCOUNT.id, "password");
  expect(compare).not.toHaveBeenCalled();
});

it("charges oversized passwords without allowing a database or bcrypt call", async () => {
  const { user, service } = fixture();
  const admission = jest.spyOn(requestLimits, "enforcePasswordRequestLimits");
  const compare = jest.spyOn(bcrypt, "compare");

  await expect(
    service.verifyPasswordCredentials(ACCOUNT.email, "x".repeat(129)),
  ).rejects.toBeInstanceOf(BadUserInputError);

  expect(admission).toHaveBeenCalledWith(ACCOUNT.email, "unknown");
  expect(user.getByMail).not.toHaveBeenCalled();
  expect(compare).not.toHaveBeenCalled();
});
