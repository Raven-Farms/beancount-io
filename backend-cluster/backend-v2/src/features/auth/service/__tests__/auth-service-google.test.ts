import "reflect-metadata";
import { AuthService } from "../auth-service";
import { ForbiddenError } from "@/shared/errors";

function createService(existing: unknown, allowedEmails: string[] = []) {
  const user = {
    getByMail: jest.fn().mockResolvedValue(existing),
    getUserByUsername: jest.fn().mockResolvedValue(null),
    create: jest.fn().mockResolvedValue({ id: "user-new" }),
  };
  const jwt = {
    create: jest.fn().mockResolvedValue({ token: "t", expireAt: new Date() }),
  };
  const createUser = jest.fn().mockResolvedValue({});
  const service = new AuthService(
    { user, jwt } as any,
    { transaction: (run: (tx: unknown) => unknown) => run({}) } as any,
    { sendMail: jest.fn().mockResolvedValue(undefined) } as any,
    {} as any,
    { getAdminClient: () => ({ admin: { createUser } }) } as any,
    {
      favaApi: { adminUser: "admin", adminPassword: "pw" },
      signup: {
        allowedEmails: new Set(allowedEmails),
        allowedDomains: new Set<string>(),
      },
    } as any,
  );
  return { service, user, jwt, createUser };
}

const identity = {
  sub: "1",
  email: "pat@example.com",
  hostedDomain: "example.com",
  givenName: "Pat",
  familyName: null,
};

describe("AuthService.signInWithGoogle", () => {
  it("signs an existing user in by email without touching registration", async () => {
    const { service, jwt, user } = createService({
      id: "user-1",
      isBlocked: false,
    });
    await service.signInWithGoogle(identity, "1.2.3.4");
    expect(jwt.create).toHaveBeenCalledWith(expect.anything(), "user-1");
    expect(user.create).not.toHaveBeenCalled();
  });

  it("refuses a blocked user and issues no session", async () => {
    const { service, jwt } = createService({ id: "user-1", isBlocked: true });
    const error = await service
      .signInWithGoogle(identity, "1.2.3.4")
      .catch((e) => e);
    expect(error).toBeInstanceOf(ForbiddenError);
    expect(error.metadata).toMatchObject({ resource: "user" });
    expect(jwt.create).not.toHaveBeenCalled();
  });

  it("refuses a new account the signup allowlist does not cover", async () => {
    const { service, user } = createService(null, ["someone-else@example.com"]);
    const error = await service
      .signInWithGoogle(identity, "1.2.3.4")
      .catch((e) => e);
    expect(error).toBeInstanceOf(ForbiddenError);
    expect(error.metadata).toMatchObject({ resource: "signup" });
    expect(user.create).not.toHaveBeenCalled();
  });

  it("creates an approved new account with no password", async () => {
    const { service, user } = createService(null, ["pat@example.com"]);
    await service.signInWithGoogle(identity, "1.2.3.4");
    expect(user.create).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        email: "pat@example.com",
        password: null,
        firstName: "Pat",
        lastName: "",
      }),
    );
  });
});
