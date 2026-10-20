import {
  authorizationUrl,
  completeGoogleSignIn,
  GoogleSignInError,
  verifyGoogleIdToken,
} from "../google-oidc";
import { CLIENT_ID, googleTestKeys } from "./google-test-keys";

const config = (hostedDomains: string[] = []) => ({
  clientId: CLIENT_ID,
  clientSecret: "test-secret",
  hostedDomains: new Set(hostedDomains),
});

async function reason(p: Promise<unknown>): Promise<string> {
  try {
    await p;
    return "accepted";
  } catch (error) {
    return error instanceof GoogleSignInError
      ? error.reason
      : `other:${String(error)}`;
  }
}

describe("verifyGoogleIdToken", () => {
  let t: Awaited<ReturnType<typeof googleTestKeys>>;
  beforeAll(async () => {
    t = await googleTestKeys();
  });
  const verify = (token: string, hd: string[] = ["example.com"]) =>
    verifyGoogleIdToken(config(hd), token, "n-1", t.keys);

  it("accepts a valid Workspace token and normalizes the identity", async () => {
    const identity = await verify(await t.sign({ email: "Pat@Example.com" }));
    expect(identity).toEqual({
      sub: "108000000000000000001",
      email: "pat@example.com",
      hostedDomain: "example.com",
      givenName: "Pat",
      familyName: "Example",
    });
  });

  it("accepts a consumer gmail.com account when no hosted domain is required", async () => {
    const token = await t.sign({ email: "pat@gmail.com", hd: undefined });
    expect((await verify(token, [])).hostedDomain).toBeNull();
  });

  it.each([
    [
      "wrong audience",
      { aud: "someone-else.apps.googleusercontent.com" },
      "google_failed",
    ],
    ["extra audience", { aud: [CLIENT_ID, "other"] }, "google_failed"],
    ["azp mismatch", { azp: "other" }, "google_failed"],
    ["wrong issuer", { iss: "https://evil.example" }, "google_failed"],
    ["expired", { exp: Math.floor(Date.now() / 1000) - 600 }, "google_failed"],
    ["missing iat", { iat: undefined }, "google_failed"],
    ["missing sub", { sub: undefined }, "google_failed"],
    ["empty sub", { sub: "" }, "google_failed"],
    ["missing nonce", { nonce: undefined }, "google_failed"],
    ["wrong nonce", { nonce: "n-2" }, "google_failed"],
    ["missing email", { email: undefined }, "google_failed"],
    ["malformed email", { email: "a@b@example.com" }, "google_failed"],
    ["unverified email", { email_verified: false }, "google_unverified"],
    [
      "email_verified as string",
      { email_verified: "true" },
      "google_unverified",
    ],
    [
      "hd differs from email domain",
      { email: "pat@other.com" },
      "google_domain",
    ],
    [
      "non-gmail without hd",
      { email: "pat@other.com", hd: undefined },
      "google_unverified",
    ],
    [
      "hd not allowed",
      { email: "pat@other.com", hd: "other.com" },
      "google_domain",
    ],
    [
      "no hd when one is required",
      { email: "pat@gmail.com", hd: undefined },
      "google_domain",
    ],
  ])("refuses %s", async (_label, claims, expected) => {
    expect(await reason(verify(await t.sign(claims)))).toBe(expected);
  });

  it("refuses a token signed by another key", async () => {
    expect(await reason(verify(await t.signWithOtherKey({})))).toBe(
      "google_failed",
    );
  });

  it("refuses a token that is not a JWT", async () => {
    expect(await reason(verify("not.a.jwt"))).toBe("google_failed");
  });
});

describe("authorizationUrl", () => {
  it("asks for the code flow with PKCE, nonce and state", () => {
    const url = new URL(
      authorizationUrl(
        config(["example.com"]),
        "https://books.example.com/cb",
        {
          state: "s",
          nonce: "n",
          codeVerifier: "v",
        },
      ),
    );
    expect(url.origin + url.pathname).toBe(
      "https://accounts.google.com/o/oauth2/v2/auth",
    );
    const q = Object.fromEntries(url.searchParams);
    expect(q).toMatchObject({
      client_id: CLIENT_ID,
      redirect_uri: "https://books.example.com/cb",
      response_type: "code",
      scope: "openid email profile",
      state: "s",
      nonce: "n",
      code_challenge_method: "S256",
      hd: "example.com",
    });
    expect(q.code_challenge).toMatch(/^[A-Za-z0-9_-]{43}$/);
    expect(q.client_secret).toBeUndefined();
  });
});

describe("PKCE", () => {
  it("sends base64url(SHA-256(verifier)) as the S256 challenge", () => {
    // Vector computed outside Node: python3 -c "import hashlib,base64;
    // print(base64.urlsafe_b64encode(hashlib.sha256(b'v').digest()).rstrip(b'=').decode())"
    const url = new URL(
      authorizationUrl(config(), "https://books.example.com/cb", {
        state: "s",
        nonce: "n",
        codeVerifier: "v",
      }),
    );
    expect(url.searchParams.get("code_challenge")).toBe(
      "TJRIXgwhrmxBzh3-e2v6zupato5AokdvUCCOUm9QYIA",
    );
  });
});

describe("completeGoogleSignIn", () => {
  it("exchanges the code with the verifier and secret, then verifies the token", async () => {
    const t = await googleTestKeys();
    const fetch = jest.fn().mockResolvedValue(
      new Response(JSON.stringify({ id_token: await t.sign({}) }), {
        status: 200,
      }),
    );
    const identity = await completeGoogleSignIn(
      config(["example.com"]),
      "https://books.example.com/cb",
      { code: "c", codeVerifier: "v", nonce: "n-1" },
      { fetch, keys: t.keys },
    );
    expect(identity.email).toBe("pat@example.com");
    const body = new URLSearchParams(fetch.mock.calls[0][1].body);
    expect(Object.fromEntries(body)).toMatchObject({
      grant_type: "authorization_code",
      code: "c",
      code_verifier: "v",
      client_secret: "test-secret",
    });
  });

  it.each([
    ["an error status", () => new Response("{}", { status: 400 })],
    [
      "no id_token",
      () =>
        new Response(JSON.stringify({ access_token: "x" }), { status: 200 }),
    ],
    ["non-JSON", () => new Response("<html>", { status: 200 })],
  ])(
    "refuses %s from the token endpoint without echoing it",
    async (_label, make) => {
      const t = await googleTestKeys();
      const error = await completeGoogleSignIn(
        config(),
        "https://books.example.com/cb",
        { code: "secret-code", codeVerifier: "secret-verifier", nonce: "n-1" },
        { fetch: jest.fn().mockResolvedValue(make()), keys: t.keys },
      ).catch((e) => e);
      expect(error).toBeInstanceOf(GoogleSignInError);
      expect(error.reason).toBe("google_failed");
      expect(error.message).not.toMatch(
        /secret-code|secret-verifier|test-secret/,
      );
    },
  );
});
