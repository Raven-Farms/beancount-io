import { isSignupAllowed } from "../signup-policy";

const policy = (emails: string[], domains: string[]) => ({
  allowedEmails: new Set(emails),
  allowedDomains: new Set(domains),
});

describe("isSignupAllowed (SIGNUP_ALLOWED_EMAILS / SIGNUP_ALLOWED_DOMAINS)", () => {
  it("is open when both lists are empty or the policy is absent", () => {
    expect(isSignupAllowed("anyone@example.com", policy([], []))).toBe(true);
    expect(isSignupAllowed("anyone@example.com", undefined)).toBe(true);
  });

  it("allows an exactly listed email, ignoring case and surrounding space", () => {
    const p = policy(["cpa@firm.example"], []);
    expect(isSignupAllowed(" CPA@Firm.Example ", p)).toBe(true);
    expect(isSignupAllowed("other@firm.example", p)).toBe(false);
  });

  it("allows addresses at an exactly listed domain only", () => {
    const p = policy([], ["example.com"]);
    expect(isSignupAllowed("a@example.com", p)).toBe(true);
    expect(isSignupAllowed("a@EXAMPLE.com", p)).toBe(true);
    expect(isSignupAllowed("a@sub.example.com", p)).toBe(false);
    expect(isSignupAllowed("a@example.com.evil.test", p)).toBe(false);
    expect(isSignupAllowed("a@notexample.com", p)).toBe(false);
  });

  it("refuses an address with more than one @", () => {
    const p = policy([], ["example.com"]);
    expect(isSignupAllowed("x@evil.test@example.com", p)).toBe(false);
    expect(isSignupAllowed("x@example.com@evil.test", p)).toBe(false);
  });

  it("refuses malformed addresses when restricted", () => {
    const p = policy(["a@example.com"], ["example.com"]);
    expect(isSignupAllowed("", p)).toBe(false);
    expect(isSignupAllowed("@example.com", p)).toBe(false);
    expect(isSignupAllowed("example.com", p)).toBe(false);
  });

  it("combines both lists", () => {
    const p = policy(["cpa@firm.example"], ["example.com"]);
    expect(isSignupAllowed("cpa@firm.example", p)).toBe(true);
    expect(isSignupAllowed("staff@example.com", p)).toBe(true);
    expect(isSignupAllowed("x@firm.example", p)).toBe(false);
  });
});
