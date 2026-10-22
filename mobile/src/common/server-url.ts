import { defaultServerUrl } from "@/config";

export {
  allowsInsecureLocalhost,
  endpointFor,
  validateServerUrl,
  type ServerUrlErrorCode,
  type ServerUrlValidation,
} from "./server-url-validation";
import {
  OFFICIAL_SERVER_URL,
  allowsInsecureLocalhost,
  endpointFor,
  validateServerUrl,
  type ServerUrlErrorCode,
} from "./server-url-validation";
import {
  CONNECTION_TIMEOUT_MS,
  discoverOAuthServer,
  OAuthDiscoveryError,
  type DiscoveryDetail,
} from "./oauth/discovery";

export function defaultRuntimeServerUrl(): string {
  const configured = validateServerUrl(defaultServerUrl, {
    allowInsecureLocalhost: allowsInsecureLocalhost(),
  });
  return configured.ok ? configured.url : OFFICIAL_SERVER_URL;
}

export type ServerConnectionResult =
  | { kind: "connected" }
  | { kind: "invalid"; code: ServerUrlErrorCode }
  | { kind: "timeout" }
  | { kind: "unreachable" }
  | { kind: "incompatible"; detail?: DiscoveryDetail }
  // Reachable and ours, but older than the app: the schema lacks fields the app
  // selects (w21/593).
  | { kind: "older" };

const HEALTH_QUERY = "query ServerHealth { health }";

/**
 * What the app needs the schema to have: the engine's fix `hint` on a ledger
 * error (2026-10-21) and the guided-setup input type (2026-10-20). Asked by
 * introspection; a server that has it switched off answers with errors, and
 * that is "cannot tell", never "older".
 */
const SCHEMA_PROBE_QUERY =
  'query ServerSchemaProbe { errorType: __type(name: "BeancountError") { fields { name } } setupType: __type(name: "LedgerSetupInput") { name } }';

/** Whether the schema answers the probe and lacks something the app uses. */
export function isOlderSchema(body: unknown): boolean {
  const data = (body as { data?: unknown } | null)?.data as
    | {
        errorType?: { fields?: Array<{ name?: string }> | null } | null;
        setupType?: { name?: string } | null;
      }
    | null
    | undefined;
  if (!data || !data.errorType) return false;
  const fields = (data.errorType.fields ?? []).map((field) => field.name);
  return !fields.includes("hint") || !data.setupType;
}

/**
 * A small contract probe for the exact public GraphQL surface the mobile app
 * needs. It is deliberately advisory: people may save a valid server while
 * offline or before joining their VPN.
 */
export async function testServerConnection(
  input: string,
  timeoutMs: number = CONNECTION_TIMEOUT_MS,
): Promise<ServerConnectionResult> {
  const validation = validateServerUrl(input);
  if (!validation.ok) {
    return { kind: "invalid", code: validation.code };
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const [healthResult, oauthResult] = await Promise.allSettled([
      fetch(endpointFor(validation.url, "api-gateway/"), {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ query: HEALTH_QUERY }),
        signal: controller.signal,
      }),
      discoverOAuthServer(validation.url, fetch, controller.signal),
    ]);
    if (controller.signal.aborted) return { kind: "timeout" };
    if (healthResult.status === "rejected") return { kind: "unreachable" };
    if (oauthResult.status === "rejected") {
      const reason: unknown = oauthResult.reason;
      return {
        kind: "incompatible",
        ...(reason instanceof OAuthDiscoveryError && reason.detail
          ? { detail: reason.detail }
          : {}),
      };
    }

    const response = healthResult.value;
    if (!response.ok) {
      return { kind: "incompatible" };
    }

    const body: unknown = await response.json();
    if (
      typeof body === "object" &&
      body !== null &&
      "data" in body &&
      typeof body.data === "object" &&
      body.data !== null &&
      "health" in body.data &&
      body.data.health === "OK"
    ) {
      // Reachable and ours; is it new enough? Advisory, like the rest: a probe
      // that fails or is refused counts as connected.
      try {
        const probe = await fetch(endpointFor(validation.url, "api-gateway/"), {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ query: SCHEMA_PROBE_QUERY }),
          signal: controller.signal,
        });
        if (probe.ok && isOlderSchema(await probe.json())) {
          return { kind: "older" };
        }
      } catch {
        // Cannot tell: connected.
      }
      return { kind: "connected" };
    }
    return { kind: "incompatible" };
  } catch {
    return controller.signal.aborted
      ? { kind: "timeout" }
      : { kind: "unreachable" };
  } finally {
    clearTimeout(timer);
  }
}
