import {
  CONNECTION_TIMEOUT_MS,
  discoverOAuthServer,
  OAuthDiscoveryError,
  type OAuthDiscovery,
} from "./discovery";

/**
 * Discovery with the same time limit as Test connection (w21/215). React
 * Native's fetch has no timeout of its own, so a server that accepts the
 * connection and never answers held Sign In for about a minute. `signal` lets
 * the caller drop the attempt, for example when the server URL is changed.
 */
export async function discoverWithTimeout(
  serverUrl: string,
  options: {
    signal?: AbortSignal;
    timeoutMs?: number;
    fetcher?: typeof fetch;
  } = {},
): Promise<OAuthDiscovery> {
  const {
    signal,
    timeoutMs = CONNECTION_TIMEOUT_MS,
    fetcher = fetch,
  } = options;
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const onAbort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener("abort", onAbort);
  try {
    return await discoverOAuthServer(serverUrl, fetcher, controller.signal);
  } catch (error: unknown) {
    if (timedOut) {
      throw new OAuthDiscoveryError(
        "unreachable",
        "The server did not respond in time",
        {
          reason: "timeout",
        },
      );
    }
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}
