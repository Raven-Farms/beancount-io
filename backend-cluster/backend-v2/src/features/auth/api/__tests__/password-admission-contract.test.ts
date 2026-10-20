import "reflect-metadata";
import {
  fakeRedisAdmission as mockFakeRedisAdmission,
  fakeRedisAdmissionState,
  fakeRedisCounter as mockFakeRedisCounter,
  fakeRedisCounterState,
} from "@/foundation/redis/__tests__/fake-redis-counter";
import { graphql } from "graphql";
import { buildSchema } from "type-graphql";
import { AuthResolver } from "../auth-resolver";
import { AuthService } from "@/features/auth/service/auth-service";
import { AuthSessionWorkflow } from "@/features/auth/workflow/auth-session-workflow";
import { graphqlRateLimitMiddleware } from "@/server/graphql/rate-limit-middleware";
import { graphqlScopeMiddleware } from "@/server/graphql/scope-middleware";
import type { Identity } from "@/server/api/identity";
import {
  BadUserInputError,
  RateLimitedError,
  ServiceUnavailableError,
} from "@/shared/errors";

jest.mock("@/foundation/redis/redis-counter", () => mockFakeRedisCounter);
jest.mock("@/foundation/redis/redis-admission", () => mockFakeRedisAdmission);

const ALICE = {
  id: "usr_alice",
  email: "alice@example.com",
  password: "synthetic-password-hash",
  isBlocked: false,
};
const authResponse = {
  token: "synthetic-session-token",
  expireAt: new Date("2030-01-01"),
};
let resolver: AuthResolver;
let schemaPromise: ReturnType<typeof buildSchema>;

async function createFixture() {
  const accounts = new Map<string, typeof ALICE>();
  const user = {
    getByMail: jest.fn(async (_db: unknown, email: string) => {
      const account = {
        ...ALICE,
        email,
        id: email === ALICE.email ? ALICE.id : `usr_${email}`,
      };
      accounts.set(account.id, account);
      return { ...account };
    }),
    getByIdForUpdate: jest.fn(
      async (_db: unknown, id: string) => accounts.get(id) ?? null,
    ),
    verifyPassword: jest.fn(
      async (_db: unknown, _id: string, password: string) =>
        password === "right-password",
    ),
  };
  const jwt = {
    create: jest.fn(async () => authResponse),
    verify: jest.fn(async () => ({
      userId: ALICE.id,
      issuedAt: 1_700_000_000,
      expiresAt: 1_900_000_000,
    })),
  };
  const models = { user, jwt };
  const db = {
    transaction: async (callback: (tx: unknown) => Promise<unknown>) =>
      callback({}),
  };
  const service = new AuthService(
    models as never,
    db as never,
    {} as never,
    {} as never,
    {} as never,
    {} as never,
    async () => false,
  );
  const ensureFollowing = jest.fn();
  const workflow = new AuthSessionWorkflow(
    service,
    { ensureFollowing },
    models as never,
    db as never,
  );
  resolver = new AuthResolver(service, workflow);
  schemaPromise ??= buildSchema({
    resolvers: [AuthResolver],
    container: { get: () => resolver },
    globalMiddlewares: [
      graphqlScopeMiddleware("enforce"),
      graphqlRateLimitMiddleware(),
    ],
    validate: true,
  });
  const schema = await schemaPromise;
  const setCookie = jest.fn();

  const execute = (
    source: string,
    ip: string,
    identity?: Identity,
    reqHeaders: Record<string, string> = {},
  ) =>
    graphql({
      schema,
      source,
      contextValue: {
        config: { env: "test" },
        clientIp: ip,
        identity,
        reqHeaders,
        koaCtx: {
          URL: new URL("https://api.example/graphql"),
          cookies: { set: setCookie },
        },
      },
    });

  return {
    user,
    jwt,
    ensureFollowing,
    setCookie,
    execute,
    signIn: (
      email = ALICE.email,
      ip = "192.0.2.1",
      password = "right-password",
      identity?: Identity,
      reqHeaders?: Record<string, string>,
    ) =>
      execute(
        `mutation {
          signIn(email: ${JSON.stringify(email)}, password: ${JSON.stringify(password)}) {
            token expireAt
          }
        }`,
        ip,
        identity,
        reqHeaders,
      ),
  };
}

beforeEach(() => {
  fakeRedisCounterState.reset();
  fakeRedisAdmissionState.reset();
});

afterEach(() => jest.restoreAllMocks());

// Password sign-in is an anonymous browser ceremony: GraphQL is its only
// eligible API surface. These tests execute the real domain chain rather than
// replacing the resolver's service with a delegation-only mock.
describe("GraphQL password admission", () => {
  it("charges every alias and does not reset request quotas after successful sign-in", async () => {
    const fixture = await createFixture();
    const aliases = Array.from(
      { length: 11 },
      (_, index) =>
        `attempt${index}: signIn(email: "alice@example.com", password: "right-password") { token }`,
    ).join("\n");

    const result = await fixture.execute(
      `mutation { ${aliases} }`,
      "192.0.2.1",
    );

    expect(result.errors).toHaveLength(1);
    expect(result.errors?.[0].path).toEqual(["attempt10"]);
    expect(result.errors?.[0].originalError).toBeInstanceOf(RateLimitedError);
    expect(fixture.user.verifyPassword).toHaveBeenCalledTimes(10);
    expect(fixture.jwt.create).toHaveBeenCalledTimes(10);
    expect(fixture.setCookie).toHaveBeenCalledTimes(10);
    expect(fixture.ensureFollowing).toHaveBeenCalledTimes(10);
  });

  it("shares the normalized account's request quota across source addresses", async () => {
    const fixture = await createFixture();
    for (let index = 0; index < 30; index += 1) {
      const result = await fixture.signIn(
        index % 2 ? " ALICE@EXAMPLE.COM " : ALICE.email,
        `192.0.2.${index + 1}`,
      );
      expect(result.errors).toBeUndefined();
    }

    const result = await fixture.signIn(ALICE.email, "198.51.100.1");

    expect(result.errors?.[0].originalError).toBeInstanceOf(RateLimitedError);
    expect(fixture.user.getByMail).toHaveBeenCalledTimes(30);
    expect(
      fixture.user.getByMail.mock.calls.every(
        ([, email]) => email === ALICE.email,
      ),
    ).toBe(true);
    expect(fixture.jwt.create).toHaveBeenCalledTimes(30);
  });

  it("holds one source to its IP quota across accounts, existing sessions, and spoofed forwarding headers", async () => {
    const fixture = await createFixture();
    for (let index = 0; index < 60; index += 1) {
      const result = await fixture.signIn(
        `person${index}@example.com`,
        "192.0.2.1",
        "right-password",
        { userId: `usr_session${index}`, method: "session", scopes: new Set() },
        {
          cookie: `authSess:beancount.io=synthetic-session-${index}`,
          "x-real-ip": `198.51.100.${index + 1}`,
          "x-forwarded-for": `203.0.113.${index + 1}`,
        },
      );
      expect(result.errors).toBeUndefined();
    }

    const result = await fixture.signIn("another@example.com", "192.0.2.1");

    expect(result.errors?.[0].originalError).toBeInstanceOf(RateLimitedError);
    expect(fixture.user.getByMail).toHaveBeenCalledTimes(60);
    expect(fixture.user.verifyPassword).toHaveBeenCalledTimes(60);
  });

  it("keeps the hourly account quota after minute quotas roll over", async () => {
    let now = Date.parse("2026-01-01T00:00:00Z");
    jest.spyOn(Date, "now").mockImplementation(() => now);
    const fixture = await createFixture();
    for (let index = 0; index < 120; index += 1) {
      if (index > 0 && index % 30 === 0) now += 60_001;
      const result = await fixture.signIn(ALICE.email, `192.0.2.${index + 1}`);
      expect(result.errors).toBeUndefined();
    }
    now += 60_001;

    const result = await fixture.signIn(ALICE.email, "198.51.100.1");

    expect(result.errors?.[0].originalError).toBeInstanceOf(RateLimitedError);
    expect(fixture.user.verifyPassword).toHaveBeenCalledTimes(120);
  });

  it("bounds a concurrent distributed password attack before expensive verification", async () => {
    const fixture = await createFixture();
    for (let index = 0; index < 2; index += 1) {
      const result = await fixture.signIn(
        ALICE.email,
        `192.0.2.${index + 1}`,
        "wrong",
      );
      expect(result.errors?.[0].originalError).toBeInstanceOf(
        BadUserInputError,
      );
    }
    // Leave eight failure slots, matching the process's bcrypt concurrency
    // ceiling, so this exercises account reservation rather than CPU shedding.
    let release: () => void = () => undefined;
    const heldPasswordChecks = new Promise<boolean>((resolve) => {
      release = () => resolve(false);
    });
    fixture.user.verifyPassword.mockImplementation(() => heldPasswordChecks);
    const attempts = Array.from({ length: 25 }, (_, index) =>
      fixture.signIn(ALICE.email, `198.51.100.${index + 1}`, "wrong"),
    );
    try {
      for (let turn = 0; turn < 30; turn += 1) {
        await new Promise<void>((resolve) => setImmediate(resolve));
        if (fixture.user.verifyPassword.mock.calls.length >= 10) break;
      }
      expect(fixture.user.verifyPassword).toHaveBeenCalledTimes(10);
      const budget = [...fakeRedisAdmissionState.failures.values()][0];
      expect(budget.failures.length + budget.pending.size).toBe(10);
      expect(fixture.jwt.create).not.toHaveBeenCalled();
    } finally {
      release();
    }
    const results = await Promise.all(attempts);

    expect(
      results.filter(
        (result) =>
          result.errors?.[0].originalError instanceof BadUserInputError,
      ),
    ).toHaveLength(8);
    expect(
      results.filter(
        (result) =>
          result.errors?.[0].originalError instanceof RateLimitedError,
      ),
    ).toHaveLength(17);
    expect([...fakeRedisAdmissionState.failures.values()][0].pending.size).toBe(
      0,
    );
    const next = await fixture.signIn(ALICE.email, "203.0.113.1");
    expect(next.errors?.[0].originalError).toBeInstanceOf(RateLimitedError);
    expect(fixture.user.verifyPassword).toHaveBeenCalledTimes(10);
  });

  it("fails closed on admission-store outage before account lookup or password verification", async () => {
    const fixture = await createFixture();
    fakeRedisAdmissionState.down = true;

    const result = await fixture.signIn();

    expect(result.errors?.[0].originalError).toBeInstanceOf(
      ServiceUnavailableError,
    );
    expect(fixture.user.getByMail).not.toHaveBeenCalled();
    expect(fixture.user.verifyPassword).not.toHaveBeenCalled();
    expect(fixture.jwt.create).not.toHaveBeenCalled();
    expect(fixture.setCookie).not.toHaveBeenCalled();
    expect(fixture.ensureFollowing).not.toHaveBeenCalled();
  });
});
