import { discoverWithTimeout } from "../bounded-discovery";
import { OAuthDiscoveryError } from "../discovery";

// A server that accepts the connection and never answers, as a paused
// container does; it only ever ends by being aborted.
const silentFetch = ((_input: RequestInfo | URL, init?: RequestInit) =>
  new Promise<Response>((_resolve, reject) => {
    init?.signal?.addEventListener("abort", () =>
      reject(new TypeError("aborted")),
    );
  })) as typeof fetch;

async function failureOf(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise;
    return "resolved";
  } catch (error: unknown) {
    return error;
  }
}

// w21/215: Sign In spun for about a minute on an unreachable server.
describe("sign-in discovery limit", () => {
  it("gives up on a silent server and says it timed out", async () => {
    const started = Date.now();
    const error = await failureOf(
      discoverWithTimeout("https://books.example.test/", {
        timeoutMs: 30,
        fetcher: silentFetch,
      }),
    );
    expect(error instanceof OAuthDiscoveryError).toBe(true);
    const failure = error as OAuthDiscoveryError;
    expect(failure.kind).toBe("unreachable");
    expect(failure.detail).toEqual({ reason: "timeout" });
    expect(Date.now() - started < 1000).toBe(true);
  });

  it("drops the attempt when the caller aborts, without calling it a timeout", async () => {
    const controller = new AbortController();
    const pending = failureOf(
      discoverWithTimeout("https://books.example.test/", {
        signal: controller.signal,
        timeoutMs: 5000,
        fetcher: silentFetch,
      }),
    );
    controller.abort();
    const error = (await pending) as OAuthDiscoveryError;
    expect(error instanceof OAuthDiscoveryError).toBe(true);
    expect(error.detail).toBe(undefined);
  });
});
