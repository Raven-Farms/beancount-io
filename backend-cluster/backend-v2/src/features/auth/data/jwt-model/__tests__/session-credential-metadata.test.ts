import { PgDialect } from "drizzle-orm/pg-core";
import type { SQL } from "drizzle-orm";
import { JwtPostgresModel } from "../postgres-impl";
import { signJwt, verifyJwt } from "@/features/auth/utils/jwt-crypto-utils";
import { resolveSessionIdentity } from "@/server/api/identity";
import { logger } from "@/shared/logger";

jest.mock("@/shared/logger", () => {
  const logger = {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
    child: jest.fn(),
  };
  logger.child.mockReturnValue(logger);
  return { logger };
});

const SECRET = "synthetic-session-metadata-signing-secret";
type SessionRow = {
  id: string;
  userId: string;
  expireAt: Date;
  createAt: Date;
  updateAt: Date;
};

/** Only persistence is synthetic: session minting, signature/expiry checks,
 * credential metadata and identity normalization use production code. */
function fixture() {
  const rows = new Map<string, SessionRow>();
  const dialect = new PgDialect();
  const db = {
    insert: () => ({
      values: (row: SessionRow) => ({
        returning: async () => {
          rows.set(row.id, row);
          return [row];
        },
      }),
    }),
    select: jest.fn(() => ({
      from: () => ({
        where: (condition: SQL) => ({
          limit: async () => {
            const { params } = dialect.sqlToQuery(condition);
            const row = rows.get(String(params[0]));
            return row && row.userId === params[1] ? [row] : [];
          },
        }),
      }),
    })),
    delete: () => ({
      where: async (condition: SQL) => {
        const { params } = dialect.sqlToQuery(condition);
        rows.delete(String(params[0]));
      },
    }),
  };
  const model = new JwtPostgresModel({ secret: SECRET, expMins: 60 });
  const database = { db: db as never, models: { jwt: model } };
  return { db, rows, model, database };
}

beforeEach(() => jest.clearAllMocks());

it("keeps a verified session id stable across requests and distinct between sessions for the same user", async () => {
  const { db, rows, model, database } = fixture();
  const first = await model.create(db as never, "usr_owner");
  const second = await model.create(db as never, "usr_owner");
  const verifiedFirst = await model.verify(db as never, first.token);
  const repeated = await model.verify(db as never, first.token);
  const verifiedSecond = await model.verify(db as never, second.token);
  const signed = await verifyJwt(first.token, SECRET);

  expect(verifiedFirst).toMatchObject({
    userId: "usr_owner",
    tokenId: signed!.jti,
    issuedAt: signed!.iat,
    expiresAt: signed!.exp,
  });
  expect(verifiedFirst).toEqual(repeated);
  expect(rows.has(verifiedFirst!.tokenId)).toBe(true);
  expect(verifiedSecond!.tokenId).not.toBe(verifiedFirst!.tokenId);
  expect(verifiedSecond!.userId).toBe(verifiedFirst!.userId);
  expect(verifiedFirst!.tokenId).not.toBe(first.token);
  const identity = await resolveSessionIdentity(first.token, database);
  expect(identity).toMatchObject({
    userId: "usr_owner",
    tokenId: verifiedFirst!.tokenId,
    method: "session",
    assurance: { type: "interactive" },
    issuedAt: signed!.iat,
    expiresAt: signed!.exp,
  });
  expect(identity!.scopes.size).toBe(0);
  expect([...identity!.capabilities!].sort()).toEqual([
    "admin",
    "read",
    "write",
  ]);
});

it("rejects forged or expired claims before looking up or exposing their credential ids", async () => {
  const { db, model, database } = fixture();
  const valid = await model.create(db as never, "usr_owner");
  const claims = (await verifyJwt(valid.token, SECRET))!;
  const parts = valid.token.split(".");
  parts[1] = Buffer.from(
    JSON.stringify({ ...claims, jti: "attacker-chosen-id" }),
  ).toString("base64url");
  const expired = await signJwt(
    { ...claims, exp: Math.floor(Date.now() / 1000) - 1 },
    SECRET,
  );

  expect(
    await resolveSessionIdentity(parts.join("."), database),
  ).toBeUndefined();
  expect(await resolveSessionIdentity(expired, database)).toBeUndefined();
  expect(db.select).not.toHaveBeenCalled();
  expect((logger.debug as jest.Mock).mock.calls).toEqual([
    ["JWT signature verification failed"],
    ["JWT signature verification failed"],
  ]);
});

it("withholds a revoked session's metadata while keeping another session for its user live", async () => {
  const { db, model, database } = fixture();
  const revoked = await model.create(db as never, "usr_owner");
  const live = await model.create(db as never, "usr_owner");
  const liveIdentity = await resolveSessionIdentity(live.token, database);

  await model.revoke(db as never, revoked.token);

  expect(await resolveSessionIdentity(revoked.token, database)).toBeUndefined();
  expect(await resolveSessionIdentity(live.token, database)).toEqual(
    liveIdentity,
  );
  expect(liveIdentity!.tokenId).toBeTruthy();
});
