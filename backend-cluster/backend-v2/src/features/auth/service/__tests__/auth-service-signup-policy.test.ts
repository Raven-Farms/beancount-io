import "reflect-metadata";
import { AuthService } from "../auth-service";
import { ForbiddenError } from "@/shared/errors";

function createService(signup?: {
  allowedEmails: Set<string>;
  allowedDomains: Set<string>;
}) {
  const user = {
    getByMail: jest.fn().mockResolvedValue(null),
    getUserByUsername: jest.fn().mockResolvedValue(null),
    create: jest.fn().mockResolvedValue({ id: "user-1" }),
  };
  const signupOtpSession = {
    createSession: jest.fn().mockResolvedValue({ id: "s-1", otp: "1234" }),
  };
  const jwt = {
    create: jest.fn().mockResolvedValue({ token: "t", expireAt: "x" }),
  };
  const createUser = jest.fn().mockResolvedValue({});
  const sendgrid = { sendMail: jest.fn().mockResolvedValue(undefined) };
  const service = new AuthService(
    { user, signupOtpSession, jwt } as any,
    { transaction: (run: (tx: unknown) => unknown) => run({}) } as any,
    sendgrid as any,
    {} as any,
    { getAdminClient: () => ({ admin: { createUser } }) } as any,
    {
      favaApi: { adminUser: "admin", adminPassword: "pw" },
      ...(signup ? { signup } : {}),
    } as any,
  );
  return { service, user, signupOtpSession, createUser, sendgrid };
}

const restricted = {
  allowedEmails: new Set(["cpa@firm.example"]),
  allowedDomains: new Set(["example.com"]),
};

let n = 0;
const params = (email: string) => ({
  email,
  password: "correct horse battery",
  firstName: "Person",
  lastName: "Example",
  username: `person_${++n}`,
  ip: "unknown",
});

describe("AuthService signup allowlist", () => {
  it("refuses to start a signup for an unlisted address, before any code is made", async () => {
    const { service, signupOtpSession, sendgrid } = createService(restricted);
    await expect(
      service.createSignUpSession(params(`stranger${++n}@elsewhere.test`)),
    ).rejects.toBeInstanceOf(ForbiddenError);
    expect(signupOtpSession.createSession).not.toHaveBeenCalled();
    expect(sendgrid.sendMail).not.toHaveBeenCalled();
  });

  it("counts refused attempts against the per-IP signup rate limit", async () => {
    const { service } = createService(restricted);
    const ip = `203.0.113.${++n % 250}`;
    for (let i = 0; i < 10; i++) {
      await expect(
        service.createSignUpSession({
          ...params(`stranger${++n}@elsewhere.test`),
          ip,
        }),
      ).rejects.toBeInstanceOf(ForbiddenError);
    }
    // The 11th attempt from that address hits the rate limit, even for a listed one.
    await expect(
      service.createSignUpSession({ ...params(`staff${++n}@example.com`), ip }),
    ).rejects.not.toBeInstanceOf(ForbiddenError);
  });

  it("starts a signup for a listed email or a listed domain", async () => {
    const { service, signupOtpSession } = createService(restricted);
    await service.createSignUpSession(params("cpa@firm.example"));
    await service.createSignUpSession(params(`staff${++n}@example.com`));
    expect(signupOtpSession.createSession).toHaveBeenCalledTimes(2);
  });

  it("refuses to create an unlisted account even if a signup session exists", async () => {
    const { service, user, createUser } = createService(restricted);
    await expect(
      service.registerUser(params(`stranger${++n}@elsewhere.test`)),
    ).rejects.toBeInstanceOf(ForbiddenError);
    expect(user.create).not.toHaveBeenCalled();
    expect(createUser).not.toHaveBeenCalled();
  });

  it("creates a listed account", async () => {
    const { service, user } = createService(restricted);
    await service.registerUser(params(`staff${++n}@example.com`));
    expect(user.create).toHaveBeenCalledTimes(1);
  });

  it("keeps signup open when no allowlist is configured", async () => {
    const empty = {
      allowedEmails: new Set<string>(),
      allowedDomains: new Set<string>(),
    };
    for (const svc of [createService(empty), createService()]) {
      await svc.service.createSignUpSession(
        params(`anyone${++n}@elsewhere.test`),
      );
      expect(svc.signupOtpSession.createSession).toHaveBeenCalledTimes(1);
    }
  });
});
