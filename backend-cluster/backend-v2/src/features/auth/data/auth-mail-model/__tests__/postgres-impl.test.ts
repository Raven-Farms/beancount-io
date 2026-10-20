import { drizzle } from "drizzle-orm/node-postgres";
import { AuthMailPostgresModel } from "../postgres-impl";
import type { AuthMail } from "../types";

const mail: AuthMail = {
  id: "aem_synthetic",
  kind: "reset",
  payload: "encrypted",
  attempts: 2,
  availableAt: new Date(),
  expiresAt: new Date(Date.now() + 300_000),
  leaseToken: "aml_synthetic",
  leaseUntil: new Date(Date.now() + 60_000),
  createdAt: new Date(),
};
function row(attempts = mail.attempts) {
  return [
    mail.id,
    mail.kind,
    mail.payload,
    attempts,
    mail.availableAt.toISOString(),
    mail.expiresAt.toISOString(),
    mail.leaseToken,
    mail.leaseUntil!.toISOString(),
    mail.createdAt.toISOString(),
  ];
}
function connection(rows: unknown[][] = []) {
  const query = jest.fn(
    async (_statement: unknown, _parameters?: unknown[]) => ({ rows }),
  );
  return { db: drizzle({ query } as never), query };
}
const text = (statement: string | { text: string }) =>
  typeof statement === "string" ? statement : statement.text;

it("claims with SKIP LOCKED and commits a counted, time-bounded lease in the same transaction", async () => {
  const { db, query } = connection();
  query.mockImplementation(async (statement: unknown) => {
    const sql = text(statement as string | { text: string });
    return {
      rows: sql.startsWith("select")
        ? [row(1)]
        : sql.startsWith("update")
          ? [row(2)]
          : [],
    };
  });

  const claimed = await new AuthMailPostgresModel().claim(db);

  const statements = query.mock.calls.map(([statement]) =>
    text(statement as string | { text: string }),
  );
  expect(statements[0]).toBe("begin");
  expect(statements[1]).toMatch(/"attempts" < \$1/);
  expect(statements[1]).toContain('"expires_at" > now()');
  expect(statements[1]).toContain('"lease_until" is null');
  expect(statements[1]).toMatch(/for update skip locked$/);
  expect(statements[2]).toContain('"attempts" = "auth_mail"."attempts" + 1');
  expect(statements[2]).toContain("interval '1 millisecond'");
  expect(query.mock.calls[2][1]).toContain(60_000);
  expect(statements[3]).toBe("commit");
  expect(claimed?.attempts).toBe(2);
});

it("commits an empty claim without issuing an update", async () => {
  const { db, query } = connection();
  await expect(new AuthMailPostgresModel().claim(db)).resolves.toBeNull();
  expect(
    query.mock.calls.map(([statement]) =>
      text(statement as string | { text: string }),
    ),
  ).toHaveLength(3);
});

it("fences prepare, acknowledgement and retry by the unexpired owner lease", async () => {
  const { db, query } = connection();
  const model = new AuthMailPostgresModel();
  await expect(model.savePayload(db, mail, "ciphertext")).resolves.toBe(false);
  await model.complete(db, mail);
  await model.retry(db, mail);

  for (const [statement, parameters] of query.mock.calls) {
    const sql = text(statement as string | { text: string });
    expect(sql).toMatch(/where .*"id" = \$\d+/);
    expect(sql).toMatch(/"lease_token" = \$\d+/);
    expect(sql).toContain('"lease_until" > now()');
    expect(parameters).toEqual(
      expect.arrayContaining([mail.id, mail.leaseToken]),
    );
  }
});

it("deletes exhausted work and cleans expired/exhausted rows only after leases end", async () => {
  const { db, query } = connection();
  const model = new AuthMailPostgresModel();
  await model.retry(db, { ...mail, attempts: 5 });
  await model.cleanup(db);
  expect(text(query.mock.calls[0][0] as { text: string })).toMatch(/^delete/);
  const cleanup = text(query.mock.calls[1][0] as { text: string });
  expect(cleanup).toContain('"expires_at" <= now()');
  expect(cleanup).toMatch(/"attempts" >= \$1/);
  expect(cleanup).toContain('"lease_until" <= now()');
});
