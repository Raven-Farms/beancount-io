import "reflect-metadata";
import bcrypt from "bcryptjs";
import {
  fakeRedisAdmission as mockFakeRedisAdmission,
  fakeRedisAdmissionState,
} from "@/foundation/redis/__tests__/fake-redis-counter";
import { BadUserInputError, ForbiddenError } from "@/shared/errors";
import { signJwt, verifyJwt } from "@/features/auth/utils/jwt-crypto-utils";
import { AuthService } from "../auth-service";

jest.mock("@/foundation/redis/redis-admission", () => mockFakeRedisAdmission);

function latch() {
  let open!: () => void;
  const promise = new Promise<void>((resolve) => {
    open = resolve;
  });
  return { promise, open };
}

type Session = { id: string; userId: string };
type State = {
  password: string;
  isBlocked: boolean;
  deleted: boolean;
  sessions: Session[];
  grants: string[];
};
type Tx = { state?: State; release?: () => void };

/** Transactional synthetic stores with the row-lock semantics used by
 * PostgreSQL SELECT FOR UPDATE and UPDATE. The model SQL test independently
 * verifies that the real user model actually requests this lock. */
async function createStore(options: {
  pauseBeforeIssuance?: boolean;
  pauseAtInsert?: boolean;
}) {
  const email = "reset-race@example.com";
  const userId = "user_reset_race";
  const secret = "synthetic-concurrency-test-signing-secret";
  let committed: State = {
    password: await bcrypt.hash("old-password", 10),
    isBlocked: false,
    deleted: false,
    sessions: [{ id: "existing-session", userId }],
    grants: ["existing-grant"],
  };
  const issuanceReached = latch();
  const allowIssuance = latch();
  const insertReached = latch();
  const allowInsert = latch();
  const resetWaitingForLock = latch();
  let nextLock = Promise.resolve();
  let serial = 0;

  async function lockRow(tx: Tx): Promise<State> {
    if (!tx.release) {
      const held = latch();
      const previous = nextLock;
      nextLock = held.promise;
      await previous;
      tx.release = held.open;
      // READ COMMITTED observes the state after the previous holder commits,
      // even when this transaction started while waiting for that holder.
      tx.state = {
        ...committed,
        sessions: [...committed.sessions],
        grants: [...committed.grants],
      };
    }
    return tx.state!;
  }

  const db = {
    async transaction<T>(run: (tx: Tx) => Promise<T>): Promise<T> {
      const tx: Tx = {};
      try {
        const result = await run(tx);
        if (tx.state) committed = tx.state;
        return result;
      } finally {
        tx.release?.();
      }
    },
  };

  async function beforeIssuance(): Promise<void> {
    if (options.pauseBeforeIssuance) {
      issuanceReached.open();
      await allowIssuance.promise;
    }
  }

  const account = (state: State) =>
    state.deleted
      ? null
      : {
          id: userId,
          email,
          password: state.password,
          isBlocked: state.isBlocked,
        };
  const user = {
    getByMail: async (_db: unknown, address: string) =>
      address === email ? account(committed) : null,
    getById: async () => account(committed),
    getByIdForUpdate: async (tx: Tx) => {
      await beforeIssuance();
      return account(await lockRow(tx));
    },
    verifyPassword: async (_db: unknown, _id: string, password: string) =>
      bcrypt.compare(password, committed.password),
    updatePassword: async (tx: Tx, _id: string, password: string) => {
      const hash = await bcrypt.hash(password, 10);
      resetWaitingForLock.open();
      (await lockRow(tx)).password = hash;
    },
  };
  const jwt = {
    create: jest.fn(async (executor: unknown, id: string) => {
      // Also pause the former unprotected implementation at its insertion
      // boundary, so reverting the fix fails assertions instead of timing out.
      await beforeIssuance();
      if (options.pauseAtInsert) {
        insertReached.open();
        await allowInsert.promise;
      }
      const state = executor === db ? committed : (executor as Tx).state!;
      const jti = `session-${++serial}`;
      const now = Math.floor(Date.now() / 1000);
      const token = await signJwt(
        { jti, sub: id, iat: now, exp: now + 3600 },
        secret,
      );
      state.sessions.push({ id: jti, userId: id });
      return { token, expireAt: new Date((now + 3600) * 1000) };
    }),
    deleteByUserId: async (tx: Tx, id: string) => {
      tx.state!.sessions = tx.state!.sessions.filter(
        (session) => session.userId !== id,
      );
    },
  };
  const emailToken = {
    findOne: async () => ({ userId }),
    findOneAndDelete: async () => ({ userId }),
  };
  const oauthGrant = {
    revokeAllForUser: async (tx: Tx) => {
      tx.state!.grants = [];
    },
  };
  const service = new AuthService(
    { user, jwt, emailToken, oauthGrant } as never,
    db as never,
    {} as never,
    {} as never,
    {} as never,
    {} as never,
    async () => false,
  );
  return {
    service,
    jwt,
    issuanceReached,
    allowIssuance,
    insertReached,
    allowInsert,
    resetWaitingForLock,
    signIn: (password = "old-password") =>
      service.loginUser({ email, password, ip: "198.51.100.7" }),
    async verifies(token: string): Promise<boolean> {
      const claims = await verifyJwt(token, secret);
      return (
        claims !== null &&
        committed.sessions.some(
          (session) =>
            session.id === claims.jti && session.userId === claims.sub,
        )
      );
    },
    block: () => {
      committed.isBlocked = true;
    },
    remove: () => {
      committed.deleted = true;
    },
    state: () => committed,
  };
}

beforeEach(() => {
  fakeRedisAdmissionState.reset();
});

it("rejects a settled old-password proof when reset commits before issuance obtains the lock", async () => {
  const store = await createStore({ pauseBeforeIssuance: true });
  const pending = store.signIn();
  const outcome = pending.then(
    (value) => ({ value }),
    (error: unknown) => ({ error }),
  );
  await store.issuanceReached.promise;

  await store.service.resetPassword("reset-token", "new-password");
  store.allowIssuance.open();

  expect(await outcome).toEqual({ error: expect.any(BadUserInputError) });
  expect(store.jwt.create).not.toHaveBeenCalled();
  expect(store.state().sessions).toEqual([]);
  expect(store.state().grants).toEqual([]);
  expect(await bcrypt.compare("old-password", store.state().password)).toBe(
    false,
  );
  const fresh = await store.signIn("new-password");
  expect(await store.verifies(fresh.token)).toBe(true);
});

it("makes reset wait for an issuing login, then revokes the session that login created", async () => {
  const store = await createStore({ pauseAtInsert: true });
  const pendingLogin = store.signIn();
  await store.insertReached.promise;
  let resetFinished = false;
  const pendingReset = store.service
    .resetPassword("reset-token", "new-password")
    .then(() => {
      resetFinished = true;
    });
  await store.resetWaitingForLock.promise;
  // Drain the reset's ready microtasks: it may proceed only when the login's
  // transaction releases the row lock, not merely after a scheduling delay.
  await new Promise<void>((resolve) => setImmediate(resolve));
  const finishedBeforeLoginCommitted = resetFinished;
  store.allowInsert.open();
  const [login] = await Promise.all([pendingLogin, pendingReset]);

  expect(finishedBeforeLoginCommitted).toBe(false);
  expect(resetFinished).toBe(true);
  expect(await store.verifies(login.token)).toBe(false);
  expect(store.state().sessions).toEqual([]);
  expect(store.state().grants).toEqual([]);
});

it.each([
  ["blocked", ForbiddenError],
  ["deleted", BadUserInputError],
] as const)(
  "revalidates a now-%s account before creating its session",
  async (change, ErrorClass) => {
    const store = await createStore({ pauseBeforeIssuance: true });
    const pending = store.signIn();
    const outcome = pending.then(
      (value) => ({ value }),
      (error: unknown) => ({ error }),
    );
    await store.issuanceReached.promise;
    if (change === "blocked") store.block();
    else store.remove();
    store.allowIssuance.open();

    expect(await outcome).toEqual({ error: expect.any(ErrorClass) });
    expect(store.jwt.create).not.toHaveBeenCalled();
  },
);
