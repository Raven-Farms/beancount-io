import "reflect-metadata";
import {
  fakeRedisAdmission as mockFakeRedisAdmission,
  fakeRedisAdmissionState,
} from "@/foundation/redis/__tests__/fake-redis-counter";
import { AuthService } from "../auth-service";
import { ForbiddenError } from "@/shared/errors";

jest.mock("@/foundation/redis/redis-admission", () => mockFakeRedisAdmission);

const ACCOUNT = {
  id: "u1",
  email: "a@example.com",
  password: "$2b$10$5mBgP06bwKPcyhp0Fg7sqeIACeCt.enWK4cu2U7FJjlUzB9as/vQS",
  isBlocked: false,
};

// AUTH_PASSWORD_ENABLED=false refuses every password ceremony before it
// touches the database, rate limits or mail.
function createService(passwordAuthEnabled: boolean | undefined) {
  const user = {
    getByMail: jest.fn().mockResolvedValue({ ...ACCOUNT }),
    getByIdForUpdate: jest.fn().mockResolvedValue({ ...ACCOUNT }),
    verifyPassword: jest.fn().mockResolvedValue(true),
    getUserByUsername: jest.fn().mockResolvedValue(null),
    create: jest.fn(),
  };
  const jwt = {
    create: jest.fn().mockResolvedValue({ token: "t", expireAt: new Date() }),
  };
  const signupOtpSession = {
    createSession: jest.fn(),
    getSession: jest.fn(),
  };
  const emailToken = { findOne: jest.fn(), create: jest.fn() };
  const sendgrid = { sendMail: jest.fn() };
  const enqueueAuthMail = jest.fn().mockResolvedValue("mail-id");
  const db = {
    transaction: jest.fn(async (run: (tx: unknown) => Promise<unknown>) =>
      run({}),
    ),
  };
  const service = new AuthService(
    { user, jwt, signupOtpSession, emailToken } as any,
    db as any,
    sendgrid as any,
    {} as any,
    {} as any,
    {
      favaApi: {},
      ...(passwordAuthEnabled === undefined ? {} : { passwordAuthEnabled }),
    } as any,
    async () => false,
    enqueueAuthMail,
  );
  return {
    service,
    user,
    jwt,
    signupOtpSession,
    emailToken,
    sendgrid,
    enqueueAuthMail,
  };
}

const calls = {
  loginUser: (s: AuthService) =>
    s.loginUser({ email: "a@example.com", password: "pw" }),
  verifyPasswordCredentials: (s: AuthService) =>
    s.verifyPasswordCredentials("a@example.com", "pw"),
  sendForgotPasswordLink: (s: AuthService) =>
    s.sendForgotPasswordLink("a@example.com"),
  requestSignInRecovery: (s: AuthService) =>
    s.requestSignInRecovery("a@example.com"),
  signInWithEmailCode: (s: AuthService) =>
    s.signInWithEmailCode({
      email: "a@example.com",
      challengeId: "c",
      code: "123456",
      password: "pw",
    } as any),
  resetPassword: (s: AuthService) => s.resetPassword("tok", "new password 123"),
  createSignUpSession: (s: AuthService) =>
    s.createSignUpSession({
      email: "a@example.com",
      password: "correct horse battery",
      firstName: "A",
      lastName: "B",
      ip: "unknown",
    }),
  finishSignupSession: (s: AuthService) =>
    s.finishSignupSession({ sessionId: "s", otp: "1234" }),
  verifySignUpOtp: (s: AuthService) =>
    s.verifySignUpOtp({ sessionId: "s", otp: "1234" }),
};

beforeEach(() => fakeRedisAdmissionState.reset());

describe("AUTH_PASSWORD_ENABLED=false", () => {
  it.each(Object.keys(calls) as (keyof typeof calls)[])(
    "%s is refused before doing anything",
    async (name) => {
      const {
        service,
        user,
        jwt,
        signupOtpSession,
        emailToken,
        sendgrid,
        enqueueAuthMail,
      } = createService(false);
      const error = await calls[name](service).catch((e) => e);
      expect(error).toBeInstanceOf(ForbiddenError);
      expect(error.metadata).toMatchObject({ resource: "password" });
      expect(user.getByMail).not.toHaveBeenCalled();
      expect(user.verifyPassword).not.toHaveBeenCalled();
      expect(jwt.create).not.toHaveBeenCalled();
      expect(signupOtpSession.createSession).not.toHaveBeenCalled();
      expect(signupOtpSession.getSession).not.toHaveBeenCalled();
      expect(emailToken.findOne).not.toHaveBeenCalled();
      expect(sendgrid.sendMail).not.toHaveBeenCalled();
      expect(enqueueAuthMail).not.toHaveBeenCalled();
    },
  );

  it.each([true, undefined])(
    "password sign-in works when the setting is %s",
    async (value) => {
      const { service, jwt } = createService(value);
      await service.loginUser({ email: "a@example.com", password: "pw" });
      expect(jwt.create).toHaveBeenCalled();
    },
  );
});
