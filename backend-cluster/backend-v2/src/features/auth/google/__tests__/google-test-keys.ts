import {
  createLocalJWKSet,
  exportJWK,
  generateKeyPair,
  SignJWT,
  type JWTVerifyGetKey,
} from "jose";

export const CLIENT_ID =
  "1234567890-abcdefghijklmnop.apps.googleusercontent.com";

/** A local stand-in for Google's signing keys. */
export async function googleTestKeys(): Promise<{
  keys: JWTVerifyGetKey;
  sign: (
    claims: Record<string, unknown>,
    opts?: { alg?: string },
  ) => Promise<string>;
  signWithOtherKey: (claims: Record<string, unknown>) => Promise<string>;
}> {
  const { publicKey, privateKey } = await generateKeyPair("RS256");
  const other = await generateKeyPair("RS256");
  const jwk = {
    ...(await exportJWK(publicKey)),
    kid: "k1",
    alg: "RS256",
    use: "sig",
  };
  const keys = createLocalJWKSet({ keys: [jwk] });
  const now = Math.floor(Date.now() / 1000);
  const base = {
    iss: "https://accounts.google.com",
    aud: CLIENT_ID,
    sub: "108000000000000000001",
    iat: now,
    exp: now + 300,
    nonce: "n-1",
    email: "pat@example.com",
    email_verified: true,
    hd: "example.com",
    given_name: "Pat",
    family_name: "Example",
  };
  const build = (claims: Record<string, unknown>) => {
    const merged: Record<string, unknown> = { ...base, ...claims };
    for (const [k, v] of Object.entries(merged))
      if (v === undefined) delete merged[k];
    return merged;
  };
  return {
    keys,
    sign: (claims, opts) =>
      new SignJWT(build(claims))
        .setProtectedHeader({ alg: opts?.alg ?? "RS256", kid: "k1" })
        .sign(privateKey),
    signWithOtherKey: (claims) =>
      new SignJWT(build(claims))
        .setProtectedHeader({ alg: "RS256", kid: "k1" })
        .sign(other.privateKey),
  };
}
