import {
  fakeRedisCounter as mockFakeRedisCounter,
  fakeRedisCounterState,
} from "@/foundation/redis/__tests__/fake-redis-counter";
import "reflect-metadata";
import { AuthService } from "../auth-service";
import { BadUserInputError, RateLimitedError } from "@/shared/errors";
import { PASSWORD_FAILURE_BUDGET } from "@/features/auth/operations/password-failure-budget";
import bcrypt from "bcryptjs";

// Password sign-in used to be limited only per address, so guesses spread over
// addresses never stopped (w0/m7). Each account now has a wrong-password
// budget, shared with Git basic auth, that no address change resets.

jest.mock("@/foundation/redis/redis-counter", () => mockFakeRedisCounter);

const ALICE = {
  id: "user-1",
  email: "alice@example.com",
  isBlocked: false,
};

function createService() {
  const user = {
    getByMail: jest.fn(async (_db: unknown, email: string) =>
      email.toLowerCase() === ALICE.email ? ALICE : null,
    ),
    getById: jest.fn(async () => ALICE),
    verifyPassword: jest.fn(
      async (_db: unknown, _id: string, password: string) =>
        password === "right-password",
    ),
    updatePassword: jest.fn(async () => undefined),
  };
  const jwt = {
    create: jest.fn(async () => ({ token: "t", expireAt: "x" })),
    deleteByUserId: jest.fn(async () => undefined),
  };
  const emailToken = {
    findOne: jest.fn(async () => ({ userId: ALICE.id })),
    findOneAndDelete: jest.fn(async () => undefined),
  };
  const oauthGrant = { revokeAllForUser: jest.fn(async () => undefined) };
  const service = new AuthService(
    { user, jwt, emailToken, oauthGrant } as never,
    { transaction: (run: (tx: unknown) => unknown) => run({}) } as never,
    {} as never,
    {} as never,
    {} as never,
    {} as never,
    async () => false,
  );
  return { service, user };
}

const signIn = (service: AuthService, email: string, password: string) =>
  service.loginUser({ email, password } as never);

async function spendBudget(service: AuthService, email: string) {
  for (let i = 0; i < PASSWORD_FAILURE_BUDGET.max; i += 1) {
    await expect(signIn(service, email, "wrong")).rejects.toBeInstanceOf(
      BadUserInputError,
    );
  }
}

beforeEach(() => fakeRedisCounterState.reset());

describe("loginUser and the per-account password budget", () => {
  it("refuses the account once its budget is spent, even the right password", async () => {
    const { service, user } = createService();
    await spendBudget(service, ALICE.email);
    user.verifyPassword.mockClear();

    await expect(
      signIn(service, ALICE.email, "right-password"),
    ).rejects.toBeInstanceOf(RateLimitedError);
    expect(user.verifyPassword).not.toHaveBeenCalled();
  });

  it("answers an unknown account exactly as a known one", async () => {
    const { service } = createService();
    await spendBudget(service, "nobody@example.com");

    const refusal = signIn(service, "nobody@example.com", "wrong");
    await expect(refusal).rejects.toBeInstanceOf(RateLimitedError);
    await expect(refusal).rejects.toThrow(
      "Too many failed sign-in attempts for this account",
    );
  });

  it("counts the account however its email is cased or padded", async () => {
    const { service } = createService();
    for (let i = 0; i < PASSWORD_FAILURE_BUDGET.max; i += 1) {
      const variant = i % 2 ? " ALICE@example.com " : ALICE.email;
      await expect(signIn(service, variant, "wrong")).rejects.toBeInstanceOf(
        BadUserInputError,
      );
    }

    await expect(signIn(service, ALICE.email, "wrong")).rejects.toBeInstanceOf(
      RateLimitedError,
    );
  });

  it("keeps each account's budget its own", async () => {
    const { service } = createService();
    await spendBudget(service, "nobody@example.com");

    await expect(
      signIn(service, ALICE.email, "right-password"),
    ).resolves.toEqual({ token: "t", expireAt: "x" });
  });

  it("starts the account afresh after a correct password", async () => {
    const { service } = createService();
    for (let i = 0; i < PASSWORD_FAILURE_BUDGET.max - 1; i += 1) {
      await signIn(service, ALICE.email, "wrong").catch(() => undefined);
    }
    await signIn(service, ALICE.email, "right-password");

    await spendBudget(service, ALICE.email);
  });

  it("starts the account afresh after a completed password reset", async () => {
    const { service } = createService();
    await spendBudget(service, ALICE.email);

    await service.resetPassword("reset-token", "new-password");

    await expect(
      signIn(service, ALICE.email, "right-password"),
    ).resolves.toEqual({ token: "t", expireAt: "x" });
  });

  it("signs in as before when Redis is unreachable", async () => {
    const { service } = createService();
    fakeRedisCounterState.down = true;
    for (let i = 0; i < PASSWORD_FAILURE_BUDGET.max + 2; i += 1) {
      await expect(
        signIn(service, ALICE.email, "wrong"),
      ).rejects.toBeInstanceOf(BadUserInputError);
    }

    await expect(
      signIn(service, ALICE.email, "right-password"),
    ).resolves.toEqual({ token: "t", expireAt: "x" });
  });
});

// New passwords are capped at bcrypt's 72 bytes (password-policy.ts); sign-in
// is not, so a longer password set before the rule still opens the account.
describe("loginUser with a password longer than 72 bytes", () => {
  it("signs in with the full password bcrypt stored truncated", async () => {
    const { service, user } = createService();
    const longPassword = "a-long-passphrase-".repeat(5) + "kept"; // 94 bytes
    const stored = await bcrypt.hash(longPassword, 4);
    user.verifyPassword.mockImplementation(async (_db, _id, password) =>
      bcrypt.compare(password, stored),
    );

    await expect(signIn(service, ALICE.email, longPassword)).resolves.toEqual({
      token: "t",
      expireAt: "x",
    });
  });
});
