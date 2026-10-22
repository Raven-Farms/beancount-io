import { validateServerUrl } from "../server-url-validation";

export const OAUTH_CLIENT_ID = "beancount-mobile";
export const OAUTH_SCOPES = [
  "openid",
  "offline_access",
  "ledger.read",
  "ledger.write",
  "ledger.admin",
] as const;
export const OAUTH_REDIRECT_URIS = [
  "io.beancount.ios:/oauth/callback",
  "io.beancount.android:/oauth/callback",
] as const;

export type OAuthDiscovery = {
  serverUrl: string;
  resource: string;
  issuer: string;
  authorizationEndpoint: string;
  tokenEndpoint: string;
  revocationEndpoint: string;
};

/** How long a server gets to answer a probe or discovery before it is called unreachable. */
export const CONNECTION_TIMEOUT_MS = 8_000;

type Fetch = typeof fetch;

function wellKnownUrl(kind: string, absoluteUrl: string): string {
  const url = new URL(absoluteUrl);
  const path = url.pathname.replace(/^\/|\/$/g, "");
  url.pathname = `/.well-known/${kind}${path ? `/${path}` : ""}`;
  url.search = "";
  url.hash = "";
  return url.toString();
}

export function issuerForServer(serverUrl: string): string {
  return serverUrl.replace(/\/$/, "");
}

export function apiResourceForServer(serverUrl: string): string {
  return new URL("v1", serverUrl).toString().replace(/\/$/, "");
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string")
    ? value
    : [];
}

export function oauthEndpointWithinIssuer(
  endpoint: unknown,
  issuer: string,
): string {
  if (typeof endpoint !== "string")
    throw new Error("OAuth endpoint is missing");
  const endpointUrl = new URL(endpoint);
  const issuerUrl = new URL(issuer);
  const prefix = issuerUrl.pathname.replace(/\/$/, "");
  if (
    endpointUrl.username ||
    endpointUrl.password ||
    endpointUrl.origin !== issuerUrl.origin ||
    (prefix &&
      endpointUrl.pathname !== prefix &&
      !endpointUrl.pathname.startsWith(`${prefix}/`))
  ) {
    throw new Error("OAuth endpoint is outside the selected issuer");
  }
  return endpointUrl.toString();
}

/**
 * Why discovery failed, in the two words the welcome screen can act on:
 * `unreachable` means no response came back at all (offline, wrong host, dead
 * port), `incompatible` means a server answered but is not a Beancount.io
 * OAuth server the app can use.
 */
export class OAuthDiscoveryError extends Error {
  constructor(
    readonly kind: "unreachable" | "incompatible",
    message: string,
    readonly detail?: DiscoveryDetail,
  ) {
    super(message);
  }
}

/**
 * What an incompatible server said that the user can act on (w21/214): it
 * answered but is not set up for sign-in, or it is a Beancount.io server that
 * names itself by another address, one the app would accept (`canonicalUrl`).
 */
export type DiscoveryDetail =
  | { reason: "not_configured" }
  | { reason: "mismatch"; canonicalUrl: string }
  | { reason: "timeout" };

const incompatible = (message: string, detail?: DiscoveryDetail) =>
  new OAuthDiscoveryError("incompatible", message, detail);

/**
 * The address a server names itself by, when it is a valid server URL other
 * than the one asked about.
 */
function canonicalServerUrl(
  claimed: unknown,
  selectedServerUrl: string,
): string | undefined {
  if (typeof claimed !== "string") return undefined;
  const validation = validateServerUrl(claimed);
  if (!validation.ok) return undefined;
  return issuerForServer(validation.url) === issuerForServer(selectedServerUrl)
    ? undefined
    : validation.url;
}

/** A server that names no usable address of its own is just incompatible. */
const mismatch = (message: string, canonicalUrl?: string) =>
  incompatible(
    message,
    canonicalUrl === undefined
      ? undefined
      : { reason: "mismatch", canonicalUrl },
  );

async function fetchJson(url: string, fetcher: Fetch, signal?: AbortSignal) {
  let response: Response;
  try {
    response = await fetcher(url, {
      headers: { accept: "application/json" },
      signal,
    });
  } catch (error: unknown) {
    throw new OAuthDiscoveryError(
      "unreachable",
      error instanceof Error ? error.message : "Could not reach the server",
    );
  }
  if (!response.ok) {
    // The backend answers 503 `oauth_not_configured` until its signing keys
    // are set: a server problem the user can name, not a wrong address.
    const failure: unknown =
      response.status === 503 ? await response.json().catch(() => null) : null;
    throw incompatible(
      "OAuth metadata is unavailable",
      isObject(failure) && failure.error === "oauth_not_configured"
        ? { reason: "not_configured" }
        : undefined,
    );
  }
  // A server answered, so a body that is not JSON (a proxy's HTML fallback
  // under 200) is a server problem, never a rejected sign-in.
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw incompatible("OAuth metadata is not JSON");
  }
  if (!isObject(body)) throw incompatible("OAuth metadata is invalid");
  return body;
}

/** An advertised endpoint that is missing, malformed, or off-issuer is the server's fault. */
function discoveredEndpoint(endpoint: unknown, issuer: string): string {
  try {
    return oauthEndpointWithinIssuer(endpoint, issuer);
  } catch (error: unknown) {
    throw incompatible(
      error instanceof Error ? error.message : "OAuth endpoint is invalid",
    );
  }
}

/** Discover and validate the exact OAuth contract for the selected server. */
export async function discoverOAuthServer(
  selectedServerUrl: string,
  fetcher: Fetch = fetch,
  signal?: AbortSignal,
): Promise<OAuthDiscovery> {
  const validation = validateServerUrl(selectedServerUrl);
  if (!validation.ok) throw incompatible("Selected server URL is invalid");

  const serverUrl = validation.url;
  const expectedIssuer = issuerForServer(serverUrl);
  const resource = apiResourceForServer(serverUrl);
  const resourceMetadata = await fetchJson(
    wellKnownUrl("oauth-protected-resource", resource),
    fetcher,
    signal,
  );
  const authorizationServers = stringArray(
    resourceMetadata.authorization_servers,
  );
  // Where the server says it lives, for the mismatch cases below: its single
  // authorization server, else its resource without the trailing /v1.
  const claimed =
    authorizationServers.length === 1
      ? authorizationServers[0]
      : typeof resourceMetadata.resource === "string"
        ? resourceMetadata.resource.replace(/\/v1$/, "")
        : undefined;
  if (resourceMetadata.resource !== resource) {
    throw mismatch(
      "Protected-resource metadata does not match the selected server",
      canonicalServerUrl(claimed, serverUrl),
    );
  }
  if (
    authorizationServers.length !== 1 ||
    authorizationServers[0] !== expectedIssuer
  ) {
    throw mismatch(
      "Authorization server does not match the selected server",
      canonicalServerUrl(claimed, serverUrl),
    );
  }
  if (
    !OAUTH_SCOPES.slice(2).every((scope) =>
      stringArray(resourceMetadata.scopes_supported).includes(scope),
    )
  ) {
    throw incompatible("Protected resource lacks required mobile scopes");
  }

  const metadata = await fetchJson(
    wellKnownUrl("oauth-authorization-server", expectedIssuer),
    fetcher,
    signal,
  );
  if (metadata.issuer !== expectedIssuer) {
    throw mismatch(
      "Authorization-server issuer mismatch",
      canonicalServerUrl(metadata.issuer, serverUrl),
    );
  }
  if (
    !stringArray(metadata.response_types_supported).includes("code") ||
    !OAUTH_SCOPES.every((scope) =>
      stringArray(metadata.scopes_supported).includes(scope),
    )
  ) {
    throw incompatible("Authorization code flow is unsupported");
  }
  if (
    stringArray(metadata.response_types_supported).some((type) =>
      type.includes("token"),
    )
  ) {
    throw incompatible(
      "Authorization server advertises an implicit response flow",
    );
  }
  if (
    !stringArray(metadata.code_challenge_methods_supported).includes("S256")
  ) {
    throw incompatible("S256 PKCE is unsupported");
  }
  if (
    !["authorization_code", "refresh_token"].every((grant) =>
      stringArray(metadata.grant_types_supported).includes(grant),
    ) ||
    !stringArray(metadata.token_endpoint_auth_methods_supported).includes(
      "none",
    ) ||
    metadata.authorization_response_iss_parameter_supported !== true
  ) {
    throw incompatible("Authorization server lacks the native OAuth contract");
  }

  return {
    serverUrl,
    resource,
    issuer: expectedIssuer,
    authorizationEndpoint: discoveredEndpoint(
      metadata.authorization_endpoint,
      expectedIssuer,
    ),
    tokenEndpoint: discoveredEndpoint(metadata.token_endpoint, expectedIssuer),
    revocationEndpoint: discoveredEndpoint(
      metadata.revocation_endpoint,
      expectedIssuer,
    ),
  };
}
