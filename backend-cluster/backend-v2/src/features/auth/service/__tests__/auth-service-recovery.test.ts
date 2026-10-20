import "reflect-metadata";
import {
  fakeRedisAdmission as mockAdmission,
  fakeRedisAdmissionState,
} from "@/foundation/redis/__tests__/fake-redis-counter";
import { consumeSignInRecoveryProof } from "@/features/auth/operations/sign-in-recovery-proof";
import { AuthService, type SignInRecoveryParams } from "../auth-service";
import {
  BadUserInputError,
  RateLimitedError,
  ServiceUnavailableError,
} from "@/shared/errors";
jest.mock("@/foundation/redis/redis-admission", () => mockAdmission);
jest.mock("@/features/auth/operations/sign-in-recovery-proof", () => ({
  consumeSignInRecoveryProof: jest.fn(),
}));

const account = {
  id: "usr_owner",
  email: "person@example.com",
  password: "stored-password-hash",
  isBlocked: false,
};
const input: SignInRecoveryParams = {
  email: account.email,
  challengeId: "aem_challenge",
  code: "123456",
  password: "correct",
  ip: "192.0.2.1",
};
function fixture() {
  const user = {
    getByMail: jest.fn(async () => ({ ...account })),
    getByIdForUpdate: jest.fn(async () => ({ ...account })),
    verifyPassword: jest.fn(
      async (_db, _id, password: string) => password === "correct",
    ),
  };
  const jwt = {
    create: jest.fn(async () => ({
      token: "issued-session",
      expireAt: new Date(0),
    })),
  };
  const db = {
    transaction: async (run: (tx: unknown) => Promise<unknown>) => run({}),
  };
  const enqueue = jest.fn(async () => "aem_challenge");
  const service = new AuthService(
    { user, jwt } as never,
    db as never,
    {} as never,
    {} as never,
    {} as never,
    { jwt: { secret: "synthetic-recovery-test-secret" } } as never,
    async () => false,
    enqueue,
  );
  return { service, user, jwt, enqueue };
}
beforeEach(() => {
  fakeRedisAdmissionState.reset();
  jest
    .mocked(consumeSignInRecoveryProof)
    .mockReset()
    .mockResolvedValue(account.id);
});

test("reset and sign-in recovery queue before account lookup with the same response path", async () => {
  const { service, user, enqueue } = fixture();
  await expect(
    service.sendForgotPasswordLink(" PERSON@example.com ", "192.0.2.1"),
  ).resolves.toBeUndefined();
  await expect(
    service.sendForgotPasswordLink("unknown@example.com", "192.0.2.1"),
  ).resolves.toBeUndefined();
  await expect(
    service.requestSignInRecovery(account.email, "192.0.2.1"),
  ).resolves.toBe("aem_challenge");
  expect(enqueue.mock.calls).toEqual([
    [account.email, "reset"],
    ["unknown@example.com", "reset"],
    [account.email, "sign-in-recovery"],
  ]);
  expect(user.getByMail).not.toHaveBeenCalled();
});

test("queue failure and Redis outage never depend on account lookup", async () => {
  const { service, user, enqueue } = fixture();
  enqueue.mockRejectedValueOnce(new ServiceUnavailableError("Email delivery"));
  await expect(
    service.sendForgotPasswordLink(account.email, "192.0.2.1"),
  ).rejects.toBeInstanceOf(ServiceUnavailableError);
  fakeRedisAdmissionState.down = true;
  await expect(
    service.requestSignInRecovery(account.email, "192.0.2.1"),
  ).rejects.toBeInstanceOf(ServiceUnavailableError);
  expect(enqueue).toHaveBeenCalledTimes(1);
  expect(user.getByMail).not.toHaveBeenCalled();
});

test("known and unknown recovery requests enqueue the same safe continuation before account lookup", async () => {
  const { service, user, enqueue } = fixture();
  const next = "/ledger/owner/books/query?q=SELECT%0A1#results";
  await service.requestSignInRecovery(account.email, "192.0.2.1", next);
  await service.requestSignInRecovery("unknown@example.com", "192.0.2.1", next);
  expect(enqueue.mock.calls).toEqual([
    [account.email, "sign-in-recovery", next],
    ["unknown@example.com", "sign-in-recovery", next],
  ]);
  expect(user.getByMail).not.toHaveBeenCalled();
});

test("rejects unsafe continuations before enqueue for both known and unknown accounts", async () => {
  const { service, user, enqueue } = fixture();
  for (const email of [account.email, "unknown@example.com"]) {
    await expect(
      service.requestSignInRecovery(email, "192.0.2.1", "/%2f%2fevil.example"),
    ).rejects.toBeInstanceOf(BadUserInputError);
  }
  expect(enqueue).not.toHaveBeenCalled();
  expect(user.getByMail).not.toHaveBeenCalled();
});

test("verified ownership can sign in through an exhausted ordinary email budget without clearing volume", async () => {
  const { service, jwt } = fixture();
  for (let n = 0; n < 30; n++) {
    await service
      .loginUser({
        email: account.email,
        password: "wrong",
        ip: `192.0.2.${n + 10}`,
      })
      .catch((error) => {
        expect(error).toBeInstanceOf(
          n < 10 ? BadUserInputError : RateLimitedError,
        );
      });
  }
  await expect(service.signInWithEmailCode(input)).resolves.toMatchObject({
    token: "issued-session",
  });
  expect(jwt.create).toHaveBeenCalledTimes(1);
  await expect(
    service.loginUser({
      email: account.email,
      password: "correct",
      ip: "192.0.2.200",
    }),
  ).rejects.toBeInstanceOf(RateLimitedError);
});

test("wrong, expired or replayed ownership proof cannot look up a user or issue a session", async () => {
  const { service, user, jwt } = fixture();
  jest.mocked(consumeSignInRecoveryProof).mockResolvedValue(null);
  await expect(service.signInWithEmailCode(input)).rejects.toBeInstanceOf(
    BadUserInputError,
  );
  expect(user.getByMail).not.toHaveBeenCalled();
  expect(jwt.create).not.toHaveBeenCalled();
});

test("a proof bound to another account and a wrong password both refuse session issuance", async () => {
  const { service, jwt } = fixture();
  jest.mocked(consumeSignInRecoveryProof).mockResolvedValueOnce("usr_other");
  await expect(service.signInWithEmailCode(input)).rejects.toBeInstanceOf(
    BadUserInputError,
  );
  await expect(
    service.signInWithEmailCode({ ...input, password: "wrong" }),
  ).rejects.toBeInstanceOf(BadUserInputError);
  expect(jwt.create).not.toHaveBeenCalled();
});

test("the verified recovery lane retains the ordinary global IP cap", async () => {
  const { service, user } = fixture();
  for (let n = 0; n < 60; n++)
    await service
      .loginUser({
        email: `p${n}@example.com`,
        password: "wrong",
        ip: input.ip,
      })
      .catch(() => undefined);
  user.getByMail.mockClear();
  await expect(service.signInWithEmailCode(input)).rejects.toBeInstanceOf(
    RateLimitedError,
  );
  expect(consumeSignInRecoveryProof).not.toHaveBeenCalled();
  expect(user.getByMail).not.toHaveBeenCalled();
});

test("recovery revalidates the locked current password before issuing a session", async () => {
  const { service, user, jwt } = fixture();
  user.getByIdForUpdate.mockResolvedValueOnce({
    ...account,
    password: "reset-password-hash",
  });
  await expect(service.signInWithEmailCode(input)).rejects.toBeInstanceOf(
    BadUserInputError,
  );
  expect(jwt.create).not.toHaveBeenCalled();
});

test("forged challenges cannot spend the mailbox owner's recovery allowance", async () => {
  const { service, user, jwt } = fixture();
  jest
    .mocked(consumeSignInRecoveryProof)
    .mockImplementation(async (_email, challengeId) =>
      challengeId === input.challengeId ? account.id : null,
    );
  for (let n = 0; n < 30; n++) {
    await expect(
      service.signInWithEmailCode({
        ...input,
        challengeId: `forged-challenge-${n}`,
        ip: `198.51.100.${n + 1}`,
      }),
    ).rejects.toBeInstanceOf(BadUserInputError);
  }
  expect(user.getByMail).not.toHaveBeenCalled();

  await expect(service.signInWithEmailCode(input)).resolves.toMatchObject({
    token: "issued-session",
  });
  expect(user.verifyPassword).toHaveBeenCalledTimes(1);
  expect(jwt.create).toHaveBeenCalledTimes(1);
});

test.each(["wrong", "correct"])(
  "bounds verified recovery to three account attempts despite changed challenges, IPs and %s passwords",
  async (password) => {
    const { service, user, jwt } = fixture();
    for (let n = 0; n < 3; n++) {
      const attempt = service.signInWithEmailCode({
        ...input,
        email: n % 2 ? " PERSON@EXAMPLE.COM " : account.email,
        challengeId: `verified-challenge-${n}`,
        ip: `198.51.100.${n + 1}`,
        password,
      });
      if (password === "wrong")
        await expect(attempt).rejects.toBeInstanceOf(BadUserInputError);
      else
        await expect(attempt).resolves.toMatchObject({
          token: "issued-session",
        });
    }

    await expect(
      service.signInWithEmailCode({
        ...input,
        challengeId: "verified-challenge-next",
        ip: "203.0.113.1",
        password,
      }),
    ).rejects.toBeInstanceOf(RateLimitedError);
    expect(consumeSignInRecoveryProof).toHaveBeenCalledTimes(4);
    expect(user.verifyPassword).toHaveBeenCalledTimes(3);
    expect(jwt.create).toHaveBeenCalledTimes(password === "correct" ? 3 : 0);
  },
);
