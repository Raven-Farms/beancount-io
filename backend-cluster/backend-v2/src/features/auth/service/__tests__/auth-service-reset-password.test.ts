import "reflect-metadata";
import { AuthService } from "../auth-service";
import { BadUserInputError } from "@/shared/errors";

// A password reset ends every session the old password issued (w0/m4). Before,
// it changed the password and left year-long sessions verifying, so a reset
// could not evict someone who already held one.

type Session = { token: string; userId: string };

/**
 * A session store and a database whose transaction commits only when its
 * callback succeeds, so a failure part-way through leaves the store untouched.
 */
function createStore() {
  let committed: Session[] = [];
  let passwords = new Map<string, string>([["user-1", "old-password"]]);
  let next = 0;

  const db = {
    async transaction<T>(run: (tx: unknown) => Promise<T>): Promise<T> {
      const tx = { sessions: [...committed], passwords: new Map(passwords) };
      const result = await run(tx);
      committed = tx.sessions;
      passwords = tx.passwords;
      return result;
    },
  };
  type Tx = { sessions: Session[]; passwords: Map<string, string> };
  const live = (db: unknown): Tx =>
    (db as Partial<Tx>).sessions
      ? (db as Tx)
      : { sessions: committed, passwords };

  const jwt = {
    create: jest.fn(async (_db: unknown, userId: string) => {
      const session = { token: `jwt-${++next}`, userId };
      committed = [...committed, session];
      return { token: session.token, expireAt: "later" };
    }),
    deleteByUserId: jest.fn(async (db: unknown, userId: string) => {
      const tx = live(db);
      tx.sessions = tx.sessions.filter((s) => s.userId !== userId);
    }),
  };
  const user = {
    getById: jest.fn(async (_db: unknown, id: string) => ({ id })),
    updatePassword: jest.fn(
      async (db: unknown, userId: string, password: string) => {
        live(db).passwords.set(userId, password);
      },
    ),
  };
  const emailToken = {
    findOne: jest.fn(async (token: string) =>
      token === "reset-token" ? { userId: "user-1" } : null,
    ),
    findOneAndDelete: jest.fn(async () => undefined),
  };

  const service = new AuthService(
    { user, jwt, emailToken } as any,
    db as any,
    {} as any,
    {} as any,
    {} as any,
    {} as any,
  );
  const verifies = (token: string) =>
    committed.some((session) => session.token === token);
  const passwordOf = (userId: string) => passwords.get(userId);
  return { service, jwt, user, emailToken, verifies, passwordOf };
}

describe("resetPassword", () => {
  it("ends every session issued before the reset", async () => {
    const { service, jwt, verifies, passwordOf } = createStore();
    const { token: browser } = await jwt.create(null, "user-1");
    const { token: cli } = await jwt.create(null, "user-1");

    await service.resetPassword("reset-token", "new-password");

    expect(verifies(browser)).toBe(false);
    expect(verifies(cli)).toBe(false);
    expect(passwordOf("user-1")).toBe("new-password");
  });

  it("leaves other users' sessions alone", async () => {
    const { service, jwt, verifies } = createStore();
    const { token: someoneElse } = await jwt.create(null, "user-2");

    await service.resetPassword("reset-token", "new-password");

    expect(verifies(someoneElse)).toBe(true);
  });

  it("lets a session made after the reset verify", async () => {
    const { service, jwt, verifies } = createStore();

    await service.resetPassword("reset-token", "new-password");
    const { token: fresh } = await jwt.create(null, "user-1");

    expect(verifies(fresh)).toBe(true);
  });

  it("revokes nothing when the password update fails", async () => {
    const { service, jwt, user, emailToken, verifies, passwordOf } =
      createStore();
    const { token: browser } = await jwt.create(null, "user-1");
    user.updatePassword.mockRejectedValueOnce(new Error("database down"));

    await expect(
      service.resetPassword("reset-token", "new-password"),
    ).rejects.toThrow("database down");

    expect(verifies(browser)).toBe(true);
    expect(passwordOf("user-1")).toBe("old-password");
    // The token is still consumed first, so it cannot be replayed.
    expect(emailToken.findOneAndDelete).toHaveBeenCalledWith("reset-token");
  });

  it("revokes nothing for an unknown reset token", async () => {
    const { service, jwt, verifies } = createStore();
    const { token: browser } = await jwt.create(null, "user-1");

    await expect(
      service.resetPassword("not-a-token", "new-password"),
    ).rejects.toBeInstanceOf(BadUserInputError);

    expect(verifies(browser)).toBe(true);
  });
});
