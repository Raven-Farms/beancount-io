import { createHash } from "node:crypto";
import { isPwnedPassword } from "../is-pwned-password";

// Pwned Passwords by k-anonymity: only a five-character SHA-1 prefix is sent,
// the match is made locally, and an unreachable service is not a refusal.

const PASSWORD = "P@ssw0rd";
const HASH = createHash("sha1").update(PASSWORD).digest("hex").toUpperCase();
const PREFIX = HASH.slice(0, 5);
const SUFFIX = HASH.slice(5);
const OTHER = "0".repeat(35);

function respondWith(body: string, status = 200) {
  return jest.fn(
    async (_url: string | URL | Request, _init?: RequestInit) =>
      new Response(body, { status }),
  );
}

describe("isPwnedPassword", () => {
  it("sends only the hash prefix, padded, and matches the suffix locally", async () => {
    const fetch = respondWith(`${OTHER}:4\r\n${SUFFIX}:1234\r\n`);

    expect(await isPwnedPassword(PASSWORD, { fetch })).toBe(true);

    const [url, init] = fetch.mock.calls[0];
    expect(String(url)).toBe(`https://api.pwnedpasswords.com/range/${PREFIX}`);
    expect(String(url)).not.toContain(SUFFIX);
    expect(init?.headers).toMatchObject({ "Add-Padding": "true" });
    expect(init?.signal).toBeInstanceOf(AbortSignal);
  });

  it.each([
    ["is not listed", respondWith(`${OTHER}:4`)],
    [
      "is only a zero-count padding line",
      respondWith(`${OTHER}:4\n${SUFFIX.toLowerCase()}:0\n`),
    ],
  ])("answers false when the password %s", async (_what, fetch) => {
    expect(await isPwnedPassword(PASSWORD, { fetch })).toBe(false);
  });

  it.each([
    ["a non-200 status", respondWith(`${SUFFIX}:9`, 503)],
    ["a body that is not a range", respondWith("<html>blocked</html>")],
    [
      "a network failure",
      jest.fn(async () => {
        throw new TypeError("fetch failed");
      }),
    ],
    [
      "a timeout",
      jest.fn(async () => {
        throw new DOMException("timed out", "TimeoutError");
      }),
    ],
  ])("accepts the password on %s", async (_what, fetch) => {
    expect(await isPwnedPassword(PASSWORD, { fetch })).toBe(false);
  });
});
