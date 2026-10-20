import "reflect-metadata";
import bcrypt from "bcryptjs";
import {
  fakeRedisAdmission as mockFakeRedisAdmission,
  fakeRedisAdmissionState,
} from "@/foundation/redis/__tests__/fake-redis-counter";
import {
  ConflictError,
  RateLimitedError,
  ServiceUnavailableError,
} from "@/shared/errors";
import type { SignupOtpSession } from "@/features/auth/data/signup-otp-session-model";
import { consumeMailDelivery } from "@/features/auth/operations/auth-mail-limits";
import { AuthService } from "../auth-service";
import { PasswordPolicyError } from "@/features/auth/utils/password-policy";

jest.mock("@/foundation/redis/redis-admission", () => mockFakeRedisAdmission);

const signup = {
  email: "person@example.com",
  password: "plinth-orbit-mangle",
  firstName: "Person",
  lastName: "Example",
  username: "kestrel",
  ip: "198.51.100.1",
};

function fixture() {
  const sessions = new Map<string, SignupOtpSession>();
  let nextSessionId = 0;
  const user = {
    getByMail: jest.fn(async (): Promise<{ id: string } | null> => null),
    getUserByUsername: jest.fn(
      async (): Promise<{ id: string } | null> => null,
    ),
  };
  const signupOtpSession = {
    createSession: jest.fn(
      async (data: Parameters<AuthService["createSignUpSession"]>[0]) => {
        for (const [id, current] of sessions) {
          if (current.email === data.email) sessions.delete(id);
        }
        const id = `session-${++nextSessionId}`;
        const session = {
          ...data,
          id,
          withDefaultLedger: data.withDefaultLedger ?? false,
          otp: "1234",
          expireAt: new Date(Date.now() + 600_000).toISOString(),
        };
        sessions.set(id, session);
        return session;
      },
    ),
    getSessionById: jest.fn(async (id: string) => sessions.get(id) ?? null),
    deleteSessionById: jest.fn(async (id: string) => {
      sessions.delete(id);
    }),
  };
  const sendgrid = { sendMail: jest.fn(async () => undefined) };
  const isPwnedPassword = jest.fn(async () => false);
  const service = new AuthService(
    { user, signupOtpSession } as never,
    {} as never,
    sendgrid as never,
    {} as never,
    {} as never,
    {} as never,
    isPwnedPassword,
  );
  return {
    user,
    signupOtpSession,
    sessions,
    sendgrid,
    isPwnedPassword,
    service,
  };
}

beforeEach(() => fakeRedisAdmissionState.reset());
afterEach(() => jest.restoreAllMocks());

it("preserves explicit existing-email signup conflicts without consuming mail delivery", async () => {
  const { service, user, signupOtpSession, sendgrid } = fixture();
  user.getByMail.mockResolvedValue({ id: "usr_existing" });

  await expect(service.createSignUpSession(signup)).rejects.toBeInstanceOf(
    ConflictError,
  );

  expect(signupOtpSession.createSession).not.toHaveBeenCalled();
  expect(sendgrid.sendMail).not.toHaveBeenCalled();
  await expect(consumeMailDelivery(signup.email)).resolves.toBe(true);
});

it("shares five signup requests per normalized email across service instances and IPs", async () => {
  const first = fixture();
  const second = fixture();
  first.user.getByMail.mockResolvedValue({ id: "usr_existing" });
  second.user.getByMail.mockResolvedValue({ id: "usr_existing" });
  for (let index = 0; index < 5; index += 1) {
    const current = index % 2 ? first : second;
    await expect(
      current.service.createSignUpSession({
        ...signup,
        email: index % 2 ? " PERSON@EXAMPLE.COM " : signup.email,
        ip: `198.51.100.${index + 1}`,
      }),
    ).rejects.toBeInstanceOf(ConflictError);
  }
  second.user.getByMail.mockClear();

  await expect(
    second.service.createSignUpSession({ ...signup, ip: "203.0.113.1" }),
  ).rejects.toBeInstanceOf(RateLimitedError);
  expect(second.user.getByMail).not.toHaveBeenCalled();
});

it.each([signup.ip, "unknown"])(
  "shares ten signup requests across different accounts for source %s",
  async (ip) => {
    const first = fixture();
    const second = fixture();
    first.user.getByMail.mockResolvedValue({ id: "usr_existing" });
    second.user.getByMail.mockResolvedValue({ id: "usr_existing" });
    for (let index = 0; index < 10; index += 1) {
      const current = index % 2 ? first : second;
      await expect(
        current.service.createSignUpSession({
          ...signup,
          email: `person${index}@example.com`,
          ip,
        }),
      ).rejects.toBeInstanceOf(ConflictError);
    }
    second.user.getByMail.mockClear();

    await expect(
      second.service.createSignUpSession({ ...signup, ip }),
    ).rejects.toBeInstanceOf(RateLimitedError);
    expect(second.user.getByMail).not.toHaveBeenCalled();
  },
);

it("suppresses a replacement email without hashing, changing its original credentials, or invalidating its OTP", async () => {
  const { service, sessions, signupOtpSession, sendgrid } = fixture();
  const originalId = await service.createSignUpSession(signup);
  const original = sessions.get(originalId)!;
  const hash = jest.spyOn(bcrypt, "hash");

  await expect(
    service.createSignUpSession({
      ...signup,
      email: " PERSON@EXAMPLE.COM ",
      password: "another-safe-password",
      firstName: "Different",
    }),
  ).rejects.toBeInstanceOf(RateLimitedError);

  expect(hash).not.toHaveBeenCalled();
  expect(signupOtpSession.createSession).toHaveBeenCalledTimes(1);
  expect(sendgrid.sendMail).toHaveBeenCalledTimes(1);
  expect(sessions.size).toBe(1);
  expect(sessions.get(originalId)).toBe(original);
  expect(await bcrypt.compare(signup.password, original.password)).toBe(true);
  const registerUser = jest.spyOn(service, "registerUser").mockResolvedValue({
    token: "synthetic-session-token",
    expireAt: new Date("2030-01-01"),
  });

  await service.verifySignUpOtp({
    sessionId: originalId,
    otp: original.otp,
    ip: signup.ip,
  });

  expect(registerUser).toHaveBeenCalledWith(
    expect.objectContaining({
      password: original.password,
      firstName: signup.firstName,
    }),
  );
});

it("honors mailbox delivery already consumed by a different authentication ceremony", async () => {
  const { service, signupOtpSession, sendgrid } = fixture();
  await expect(consumeMailDelivery(signup.email)).resolves.toBe(true);

  await expect(service.createSignUpSession(signup)).rejects.toBeInstanceOf(
    RateLimitedError,
  );

  expect(signupOtpSession.createSession).not.toHaveBeenCalled();
  expect(sendgrid.sendMail).not.toHaveBeenCalled();
});

it("allows a replacement session and fresh delivery after the cooldown", async () => {
  let now = Date.parse("2026-01-01T00:00:00Z");
  jest.spyOn(Date, "now").mockImplementation(() => now);
  const { service, sessions, sendgrid } = fixture();
  const originalId = await service.createSignUpSession(signup);
  now += 60_001;

  const replacementId = await service.createSignUpSession({
    ...signup,
    password: "another-safe-password",
  });

  expect(replacementId).not.toBe(originalId);
  expect(sessions.has(originalId)).toBe(false);
  expect(sessions.has(replacementId)).toBe(true);
  expect(sendgrid.sendMail).toHaveBeenCalledTimes(2);
});

it("retains cheap signup validation and password policy before any delivery", async () => {
  const { service, signupOtpSession, sendgrid } = fixture();

  await expect(
    service.createSignUpSession({ ...signup, password: "short" }),
  ).rejects.toBeInstanceOf(PasswordPolicyError);

  expect(signupOtpSession.createSession).not.toHaveBeenCalled();
  expect(sendgrid.sendMail).not.toHaveBeenCalled();
  await expect(consumeMailDelivery(signup.email)).resolves.toBe(true);
});

it("fails closed before account lookup when signup admission is unavailable", async () => {
  const { service, user, signupOtpSession, sendgrid } = fixture();
  fakeRedisAdmissionState.down = true;

  await expect(service.createSignUpSession(signup)).rejects.toBeInstanceOf(
    ServiceUnavailableError,
  );

  expect(user.getByMail).not.toHaveBeenCalled();
  expect(signupOtpSession.createSession).not.toHaveBeenCalled();
  expect(sendgrid.sendMail).not.toHaveBeenCalled();
});
