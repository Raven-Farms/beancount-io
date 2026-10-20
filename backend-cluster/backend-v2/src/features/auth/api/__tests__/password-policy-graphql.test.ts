import "reflect-metadata";
import { graphql, type GraphQLError } from "graphql";
import { buildSchema } from "type-graphql";
import { AuthResolver } from "../auth-resolver";
import { AuthService } from "@/features/auth/service/auth-service";
import { graphqlScopeMiddleware } from "@/server/graphql/scope-middleware";
import { formatError } from "@/server/graphql/format-error";

jest.mock("@/foundation/redis/redis-counter", () => ({
  resetCount: jest.fn(async () => undefined),
}));

// The dashboard says which rule a refused new password broke by reading
// `extensions.passwordPolicy`. Pin that contract where clients meet it: the
// GraphQL mutations, formatted as Apollo sends them.

const isPwnedPassword = jest.fn(async (_password: string) => false);
const createSession = jest.fn(async () => ({ id: "s-1", otp: "1234" }));
const findOneAndDelete = jest.fn(async () => undefined);

const service = new AuthService(
  {
    user: {
      getByMail: async () => null,
      getUserByUsername: async () => null,
      getById: async () => ({
        id: "usr_pat",
        email: "pat@example.org",
        ledger_username: "kestrel",
      }),
      updatePassword: async () => undefined,
    },
    jwt: { deleteByUserId: async () => undefined },
    oauthGrant: { revokeAllForUser: async () => undefined },
    signupOtpSession: {
      createSession,
      getSessionById: async () => ({ expireAt: new Date("2030-01-01") }),
    },
    emailToken: {
      findOne: async () => ({ userId: "usr_pat" }),
      findOneAndDelete,
    },
  } as never,
  { transaction: async (run: (tx: unknown) => unknown) => run({}) } as never,
  { sendMail: async () => undefined } as never,
  {} as never,
  {} as never,
  {} as never,
  isPwnedPassword,
);
const resolver = new AuthResolver(service, {} as never);
const schemaPromise = buildSchema({
  resolvers: [AuthResolver],
  container: { get: () => resolver },
  globalMiddlewares: [graphqlScopeMiddleware("enforce")],
  validate: true,
});

beforeEach(() => jest.clearAllMocks());

/** The first error, formatted as a client receives it, or undefined. */
async function firstError(source: string, password: string) {
  const result = await graphql({
    schema: await schemaPromise,
    source,
    variableValues: { password },
    contextValue: { config: { env: "test" }, clientIp: "unknown" },
  });
  const error = result.errors?.[0] as GraphQLError | undefined;
  return error && formatError(error.toJSON(), error);
}

const SIGN_UP = `mutation($password: String!) {
  signUp(email: "pat@example.org", password: $password, firstName: "Pat",
    lastName: "Lee", username: "kestrel") { sessionId }
}`;
const RESET = `mutation($password: String!) {
  resetPassword(token: "reset-token", newPassword: $password) { success }
}`;

describe.each([
  ["signUp", SIGN_UP],
  ["resetPassword", RESET],
])("%s password policy over GraphQL", (_name, source) => {
  it.each([
    ["short", "MIN_LENGTH"],
    ["a".repeat(80), "MAX_LENGTH"],
    ["kestrel2024", "TOO_SIMILAR"],
  ])("refuses %j as %s", async (password, passwordPolicy) => {
    expect((await firstError(source, password))?.extensions).toMatchObject({
      code: "VALIDATION_FAILED",
      field: "password",
      passwordPolicy,
      hint: expect.any(String),
    });
    expect(isPwnedPassword).not.toHaveBeenCalled();
  });

  it("refuses a breached password as BREACHED", async () => {
    isPwnedPassword.mockResolvedValueOnce(true);
    expect((await firstError(source, "password123"))?.extensions).toMatchObject(
      { code: "VALIDATION_FAILED", passwordPolicy: "BREACHED" },
    );
    expect(createSession).not.toHaveBeenCalled();
    expect(findOneAndDelete).not.toHaveBeenCalled();
  });

  it("accepts a password the policy allows", async () => {
    expect(await firstError(source, "plinth-orbit-mangle")).toBeUndefined();
    expect(isPwnedPassword).toHaveBeenCalledWith("plinth-orbit-mangle");
  });
});
