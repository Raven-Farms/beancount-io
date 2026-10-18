import { drizzle } from "drizzle-orm/node-postgres";
import { OauthGrantPostgresModel } from "../postgres-impl";

// The statement itself is the behavior: which rows of the shared provider table
// a password reset deletes (w0/m4/t002). It was also run against Postgres 16
// with grants, refresh tokens, codes, sessions, clients and interactions for
// two users whose ids share a prefix; only the target user's rows went.

function capturingDb() {
  const queries: { text: string; values: unknown[] }[] = [];
  const client = {
    query: async (
      config: { text: string; values?: unknown[] },
      values?: unknown[],
    ) => {
      queries.push({
        text: config.text,
        values: values ?? config.values ?? [],
      });
      return { rows: [], rowCount: 0 };
    },
  };
  return { db: drizzle({ client: client as never }), queries };
}

describe("OauthGrantPostgresModel.revokeAllForUser", () => {
  it("deletes the user's rows and every row issued under their grants in one statement", async () => {
    const { db, queries } = capturingDb();

    await new OauthGrantPostgresModel().revokeAllForUser(db, "usr_alice");

    expect(queries).toHaveLength(1);
    const [{ text, values }] = queries;
    expect(text).toMatch(/^delete from "oauth_adapter_storage"/);
    // Account-wide ("usr_alice") and ledger-pinned ("usr_alice:owner/name")
    // accountIds are matched on their user segment, never by prefix.
    expect(text).toContain(
      `split_part("oauth_adapter_storage"."payload"->>'accountId', ':', 1) = $1`,
    );
    expect(text).not.toMatch(/like/i);
    // Refresh tokens and codes are reached through their grant id as well.
    expect(text).toMatch(
      /"oauth_adapter_storage"\."grant_id" in \(select "id" from "oauth_adapter_storage" where \("oauth_adapter_storage"\."model" = \$2 and split_part/,
    );
    expect(values).toEqual(["usr_alice", "Grant", "usr_alice"]);
  });
});
