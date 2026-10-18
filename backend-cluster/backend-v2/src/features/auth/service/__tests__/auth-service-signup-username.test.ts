import "reflect-metadata";
import { AuthService } from "../auth-service";
import { BadUserInputError } from "@/shared/errors";
import { usernameFromEmail } from "@/features/auth/utils/username-rule";

// Sign-up holds a username to the rule renames already follow (w0/036): 1–20
// lowercase letters, digits and underscores. Only the dashboard form checked
// it before, and a sign-up without one took the email's local part as is
// (w0/046).

function createService(taken: string[] = []) {
  const takenLower = new Set(taken.map((name) => name.toLowerCase()));
  const user = {
    getByMail: jest.fn().mockResolvedValue(null),
    // The real lookup compares lower-cased names.
    getUserByUsername: jest.fn(async (_db: unknown, name: string) =>
      takenLower.has(name.toLowerCase()) ? { id: "someone" } : null,
    ),
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
    { favaApi: { adminUser: "admin", adminPassword: "pw" } } as any,
  );
  return { service, user, signupOtpSession, createUser, sendgrid };
}

let emailCounter = 0;
const signUpParams = (username?: string | null) => ({
  // A fresh address per call: sign-up is rate limited per email.
  email: `person${++emailCounter}@example.com`,
  password: "correct horse battery",
  firstName: "Person",
  lastName: "Example",
  username,
  ip: "unknown",
});

describe("createSignUpSession username", () => {
  it.each(["John.Doe", "UPPER", "has space", "a".repeat(21), "dash-ed"])(
    "refuses %j on the username field before sending a code",
    async (username) => {
      const { service, signupOtpSession, sendgrid } = createService();
      const refusal = service.createSignUpSession(signUpParams(username));
      await expect(refusal).rejects.toBeInstanceOf(BadUserInputError);
      await expect(refusal).rejects.toMatchObject({
        metadata: { field: "username" },
      });
      expect(signupOtpSession.createSession).not.toHaveBeenCalled();
      expect(sendgrid.sendMail).not.toHaveBeenCalled();
    },
  );

  it("accepts a username in the rule", async () => {
    const { service, signupOtpSession } = createService();
    await service.createSignUpSession(signUpParams("ana_99"));
    expect(signupOtpSession.createSession).toHaveBeenCalledWith(
      expect.objectContaining({ username: "ana_99" }),
      10,
    );
  });

  it("still lets a sign-up omit the username", async () => {
    const { service, signupOtpSession } = createService();
    await service.createSignUpSession(signUpParams(null));
    expect(signupOtpSession.createSession).toHaveBeenCalledWith(
      expect.objectContaining({ username: null }),
      10,
    );
  });
});

describe("registerUser username", () => {
  const register = (
    service: AuthService,
    email: string,
    username?: string | null,
  ) =>
    service.registerUser({
      email,
      password: "hashed",
      firstName: "Person",
      lastName: "Example",
      username,
      ip: "unknown",
    } as Parameters<AuthService["registerUser"]>[0]);

  it("derives a name in the rule from the email when none was chosen", async () => {
    const { service, user, createUser } = createService();
    await register(service, "John.Doe+tag@example.com");
    expect(user.create).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ ledger_username: "john_doe_tag" }),
    );
    expect(createUser).toHaveBeenCalledWith(
      expect.objectContaining({ username: "john_doe_tag" }),
      expect.anything(),
    );
  });

  it("numbers a derived name that someone already has, ignoring case", async () => {
    const { service, createUser } = createService(["John_Doe"]);
    await register(service, "john.doe@example.com");
    expect(createUser).toHaveBeenCalledWith(
      expect.objectContaining({ username: "john_doe2" }),
      expect.anything(),
    );
  });

  it("refuses a chosen name outside the rule", async () => {
    const { service, createUser } = createService();
    await expect(
      register(service, "x@example.com", "Bad.Name"),
    ).rejects.toBeInstanceOf(BadUserInputError);
    expect(createUser).not.toHaveBeenCalled();
  });
});

describe("usernameFromEmail", () => {
  const free = async () => false;

  it.each([
    ["john.doe+x@example.com", "john_doe_x"],
    ["ANA@example.com", "ana"],
    ["élodie@example.com", "_lodie"],
    ["a.very.long.local.part.indeed@example.com", "a_very_long_local_pa"],
    ["@example.com", "user"],
  ])("turns %s into %s", async (email, username) => {
    expect(await usernameFromEmail(email, free)).toBe(username);
  });

  it("keeps a numbered name within 20 characters", async () => {
    const taken = new Set(["a_very_long_local_pa", "a_very_long_local_p2"]);
    expect(
      await usernameFromEmail(
        "a.very.long.local.part.indeed@example.com",
        async (name) => taken.has(name),
      ),
    ).toBe("a_very_long_local_p3");
  });
});
