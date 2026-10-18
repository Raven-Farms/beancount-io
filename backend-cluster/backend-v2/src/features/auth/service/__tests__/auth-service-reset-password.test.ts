import "reflect-metadata";
import { AuthService } from "../auth-service";
import { BadUserInputError } from "@/shared/errors";

// A password reset ends every session and OAuth grant the old password issued
// (w0/m4). Before, it changed the password and left year-long sessions and
// refresh tokens working, so a reset could not evict someone who held one.

type Session = { token: string; userId: string };
type Grant = { id: string; userId: string };

/**
 * A session store and a database whose transaction commits only when its
 * callback succeeds, so a failure part-way through leaves the store untouched.
 */
function createStore() {
  let committed: Session[] = [];
  let grants: Grant[] = [
    { id: "mobile", userId: "user-1" },
    { id: "connector", userId: "user-1" },
    { id: "theirs", userId: "user-2" },
  ];
  let passwords = new Map<string, string>([["user-1", "old-password"]]);
  let next = 0;

  const db = {
    async transaction<T>(run: (tx: unknown) => Promise<T>): Promise<T> {
      const tx = {
        sessions: [...committed],
        grants: [...grants],
        passwords: new Map(passwords),
      };
      const result = await run(tx);
      committed = tx.sessions;
      grants = tx.grants;
      passwords = tx.passwords;
      return result;
    },
  };
  type Tx = {
    sessions: Session[];
    grants: Grant[];
    passwords: Map<string, string>;
  };
  // The service hands the models only the transaction.
  const live = (tx: unknown) => tx as Tx;

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
  const oauthGrant = {
    revokeAllForUser: jest.fn(async (db: unknown, userId: string) => {
      const tx = live(db);
      tx.grants = tx.grants.filter((g) => g.userId !== userId);
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
    { user, jwt, oauthGrant, emailToken } as any,
    db as any,
    {} as any,
    {} as any,
    {} as any,
    {} as any,
  );
  const verifies = (token: string) =>
    committed.some((session) => session.token === token);
  const passwordOf = (userId: string) => passwords.get(userId);
  const grantsOf = (userId: string) =>
    grants.filter((g) => g.userId === userId).map((g) => g.id);
  return {
    service,
    jwt,
    oauthGrant,
    user,
    emailToken,
    verifies,
    passwordOf,
    grantsOf,
  };
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

  it("revokes every OAuth grant the user holds", async () => {
    const { service, grantsOf } = createStore();

    await service.resetPassword("reset-token", "new-password");

    expect(grantsOf("user-1")).toEqual([]);
  });

  it("leaves other users' sessions and grants alone", async () => {
    const { service, jwt, verifies, grantsOf } = createStore();
    const { token: someoneElse } = await jwt.create(null, "user-2");

    await service.resetPassword("reset-token", "new-password");

    expect(verifies(someoneElse)).toBe(true);
    expect(grantsOf("user-2")).toEqual(["theirs"]);
  });

  it("lets a session made after the reset verify", async () => {
    const { service, jwt, verifies } = createStore();

    await service.resetPassword("reset-token", "new-password");
    const { token: fresh } = await jwt.create(null, "user-1");

    expect(verifies(fresh)).toBe(true);
  });

  it("revokes nothing when the password update fails", async () => {
    const { service, jwt, user, emailToken, verifies, passwordOf, grantsOf } =
      createStore();
    const { token: browser } = await jwt.create(null, "user-1");
    user.updatePassword.mockRejectedValueOnce(new Error("database down"));

    await expect(
      service.resetPassword("reset-token", "new-password"),
    ).rejects.toThrow("database down");

    expect(verifies(browser)).toBe(true);
    expect(passwordOf("user-1")).toBe("old-password");
    expect(grantsOf("user-1")).toEqual(["mobile", "connector"]);
    // The token is still consumed first, so it cannot be replayed.
    expect(emailToken.findOneAndDelete).toHaveBeenCalledWith("reset-token");
  });

  it("keeps the old password and sessions when grant revocation fails", async () => {
    const { service, jwt, oauthGrant, verifies, passwordOf, grantsOf } =
      createStore();
    const { token: browser } = await jwt.create(null, "user-1");
    oauthGrant.revokeAllForUser.mockRejectedValueOnce(new Error("timeout"));

    await expect(
      service.resetPassword("reset-token", "new-password"),
    ).rejects.toThrow("timeout");

    // All or nothing: a reset never reports success with a grant left behind.
    expect(verifies(browser)).toBe(true);
    expect(passwordOf("user-1")).toBe("old-password");
    expect(grantsOf("user-1")).toEqual(["mobile", "connector"]);
  });

  it("revokes nothing for an unknown reset token", async () => {
    const { service, jwt, verifies, grantsOf } = createStore();
    const { token: browser } = await jwt.create(null, "user-1");

    await expect(
      service.resetPassword("not-a-token", "new-password"),
    ).rejects.toBeInstanceOf(BadUserInputError);

    expect(verifies(browser)).toBe(true);
    expect(grantsOf("user-1")).toEqual(["mobile", "connector"]);
  });
});
