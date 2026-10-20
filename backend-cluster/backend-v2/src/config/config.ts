import { getOptionalJwks } from "./jwks";
import type { ScopeEnforcementMode } from "@/server/api/op-class";
import { z } from "zod";

// Type definitions for configuration
interface ServerConfig {
  proxy: boolean;
  port: number;
  url: string;
  /**
   * Extra browser origins allowed by CORS with credentials (CORS_ALLOWED_ORIGINS,
   * comma-separated), in addition to beancount.io and localhost. For self-hosts
   * whose dashboard calls the API on another host.
   */
  corsAllowedOrigins: ReadonlySet<string>;
}

const DOMAIN_NAME =
  /^(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/;

/** SIGNUP_ALLOWED_EMAILS: comma-separated addresses, lowercased. Fails at boot on a malformed entry. */
export function parseSignupAllowedEmails(
  value: string | undefined,
): ReadonlySet<string> {
  const emails = new Set<string>();
  for (const entry of (value ?? "").split(",")) {
    const email = entry.trim().toLowerCase();
    if (!email) continue;
    // Same validator signup applies to the address, plus a real domain name.
    if (
      !z.email().safeParse(email).success ||
      !DOMAIN_NAME.test(email.slice(email.indexOf("@") + 1))
    ) {
      throw new Error(
        `SIGNUP_ALLOWED_EMAILS: not an email address ${JSON.stringify(entry.trim())}`,
      );
    }
    emails.add(email);
  }
  // A non-blank value with no entries (e.g. ", ,") would silently mean "open".
  if (value?.trim() && emails.size === 0) {
    throw new Error("SIGNUP_ALLOWED_EMAILS: set but lists no addresses");
  }
  return emails;
}

/** SIGNUP_ALLOWED_DOMAINS: comma-separated bare domains (no "@", no wildcards), lowercased. */
export function parseSignupAllowedDomains(
  value: string | undefined,
): ReadonlySet<string> {
  return parseDomainList(value, "SIGNUP_ALLOWED_DOMAINS");
}

function parseDomainList(
  value: string | undefined,
  name: string,
): ReadonlySet<string> {
  const domains = new Set<string>();
  for (const entry of (value ?? "").split(",")) {
    const domain = entry.trim().toLowerCase();
    if (!domain) continue;
    if (!DOMAIN_NAME.test(domain)) {
      throw new Error(
        `${name}: not a bare domain ${JSON.stringify(entry.trim())}`,
      );
    }
    domains.add(domain);
  }
  if (value?.trim() && domains.size === 0) {
    throw new Error(`${name}: set but lists no domains`);
  }
  return domains;
}

/** AUTH_PASSWORD_ENABLED: unset or "true" = on, "false" = off; anything else fails at boot. */
export function parsePasswordAuthEnabled(value: string | undefined): boolean {
  const v = value?.trim().toLowerCase() ?? "";
  if (v === "" || v === "true") return true;
  if (v === "false") return false;
  throw new Error(
    `AUTH_PASSWORD_ENABLED: expected "true" or "false", got ${JSON.stringify(value)}`,
  );
}

/** Both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET, or neither. */
export function parseGoogleAuthConfig(env: {
  GOOGLE_CLIENT_ID?: string;
  GOOGLE_CLIENT_SECRET?: string;
  GOOGLE_HOSTED_DOMAINS?: string;
}): GoogleAuthConfig | null {
  const clientId = env.GOOGLE_CLIENT_ID?.trim() ?? "";
  const clientSecret = env.GOOGLE_CLIENT_SECRET?.trim() ?? "";
  const hostedDomains = parseDomainList(
    env.GOOGLE_HOSTED_DOMAINS,
    "GOOGLE_HOSTED_DOMAINS",
  );
  if (!clientId && !clientSecret) {
    if (hostedDomains.size > 0) {
      throw new Error(
        "GOOGLE_HOSTED_DOMAINS is set but GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET are not",
      );
    }
    return null;
  }
  if (!clientId || !clientSecret) {
    throw new Error(
      "Set both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET, or neither",
    );
  }
  if (!/^[0-9]+(?:-[a-z0-9]+)?\.apps\.googleusercontent\.com$/.test(clientId)) {
    throw new Error("GOOGLE_CLIENT_ID is not a Google OAuth client ID");
  }
  return { clientId, clientSecret, hostedDomains };
}

export function parseCookieDomain(
  value: string | undefined,
): string | null | undefined {
  const trimmed = value?.trim();
  if (!trimmed) return undefined;
  if (trimmed === "host-only") return null;
  // A bare hostname with an optional leading dot; anything else (scheme, port,
  // path, ";") would break or extend the Set-Cookie header. Fail at boot.
  if (
    !/^\.?(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/i.test(
      trimmed,
    )
  ) {
    throw new Error(
      `AUTH_COOKIE_DOMAIN: expected "host-only" or a domain like .example.com, got ${JSON.stringify(trimmed)}`,
    );
  }
  return trimmed.toLowerCase();
}

export function parseCorsAllowedOrigins(
  value: string | undefined,
): ReadonlySet<string> {
  const origins = new Set<string>();
  for (const entry of (value ?? "").split(",")) {
    const trimmed = entry.trim();
    if (!trimmed) continue;
    if (!/^[a-z][a-z0-9+.-]*:/i.test(trimmed) || !/^https?:/i.test(trimmed)) {
      throw new Error(`CORS_ALLOWED_ORIGINS: unsupported origin ${trimmed}`);
    }
    // Exact origins only, checked on the raw text before URL normalization
    // (which would quietly turn "/path/..", "?" or "#" into a bare origin):
    // scheme://host[:port] with an optional trailing "/", no wildcards.
    if (
      !/^https?:\/\/([a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*|\[[0-9a-f:.]+\])(:\d{1,5})?\/?$/i.test(
        trimmed,
      )
    ) {
      throw new Error(`CORS_ALLOWED_ORIGINS: not a bare origin ${trimmed}`);
    }
    origins.add(new URL(trimmed).origin);
  }
  return origins;
}

interface LoggerConfig {
  enabled: boolean;
  level: string;
}

interface PostgresConfig {
  uri: string;
}

interface SendGridConfig {
  apiKey: string;
}

interface AnalyticsConfig {
  gaMeasurementId: string;
}

interface JwtConfig {
  secret: string;
  /** Token lifetime in minutes. Default 525600 (365 days); override via AUTH_JWT_EXP_MINUTES for local testing. */
  expMins: number;
  /**
   * Domain attribute of the session cookie (AUTH_COOKIE_DOMAIN).
   * - `undefined` (unset): `.beancount.io` in production, host-only elsewhere.
   * - `null` (`host-only`): no Domain attribute, for self-hosts that serve the
   *   API on the dashboard's own host.
   * - a string (e.g. `.example.com`): shared across that domain's subdomains.
   */
  cookieDomain: string | null | undefined;
}

interface FavaAPIConfig {
  baseUrl: string;
  adminUser: string;
  adminPassword: string;
}

interface DashboardConfig {
  url: string;
}

/**
 * Native app-link vouchers for `/.well-known/apple-app-site-association` and
 * `/.well-known/assetlinks.json`. Unset when a self-host has no native build —
 * those routes then 404 rather than advertising someone else's app.
 */
interface AppLinksConfig {
  /** Apple Developer Team ID (e.g. Beancount.io production: `PTLM7BZQMM`). */
  appleTeamId: string | null;
  /** Play App Signing SHA-256 fingerprints, comma-separated in env. */
  androidSha256Fingerprints: readonly string[];
}

/**
 * Domain proof for the official MCP Registry (registry.modelcontextprotocol.io):
 * the public record a `mcp-publisher login http` signature is verified against,
 * served at `/.well-known/mcp-registry-auth`. Unset on a self-host — serving
 * Beancount.io's key there would let Beancount.io publish under that domain's
 * registry namespace.
 */
interface McpRegistryConfig {
  /** `v=MCPv1; k=ed25519; p=<base64 public key>` (`k=ecdsap384` for P-384), or null. */
  authProof: string | null;
}

export interface GiteaConfig {
  hostname: string;
  internalHostname: string;
  httpPort: number;
  /**
   * Fully-qualified base URL for host->Gitea API calls, derived once from
   * internalHostname/httpPort/GITEA_PROTOCOL. Use this instead of rebuilding
   * `http://<host>:3000` at each call site: an off-cluster Gitea is reached
   * over https on 443, which a hardcoded scheme and port cannot express.
   */
  internalBaseUrl: string;
  externalHttpPort: number;
  /** Port advertised in clone URLs. */
  sshPort: number;
  /** Where Gitea's SSH listens inside the compose network. */
}

interface SshProxyConfig {
  enabled: boolean;
  port: number;
  hostKey: string;
}

interface BlockEdenConfig {
  accessKey: string;
}

interface ClaudeCodeSandboxConfig {
  apiUrl: string;
}

interface AgentConfig {
  mode: "self-hosted" | "sandbox";
  sandboxApiUrl: string;
}

interface StripeConfig {
  webhookSecret: string;
  publicKey: string;
  privateKey: string;
}

interface RedisConfig {
  uri: string;
}

export interface AssetS3Config {
  endpoint: string;
  region: string;
  bucket: string;
  accessKeyId: string;
  secretAccessKey: string;
  uploadUrlExpiration: number; // seconds
  downloadUrlExpiration: number; // seconds
}

interface LokiConfig {
  host: string;
}

type PlaidEnvironment = "sandbox" | "development" | "production";

export interface PlaidConfig {
  clientId: string;
  secret: string;
  environment: PlaidEnvironment;
  webhookUrl: string;
}

export type Environment = "production" | "development" | "test";

interface OAuthConfig {
  issuer: string;
  /** Public dashboard/front-door origin that serves OAuth interaction pages. */
  interactionUrl: string;
  /** Undefined means OAuth is unavailable but legacy login remains available. */
  jwks?: { keys: object[] };
  unavailableReason?: string;
  /**
   * Deployment secret for the static Discourse identity client. Its non-secret
   * metadata and every other OAuth client policy live together in
   * features/oauth/data/config.ts. An empty value omits this optional client.
   */
  discourseClientSecret: string;
}

/**
 * The API suite's own settings (ADR 0006). Authorization policy stays
 * hard-coded; development-only test affordances are explicitly inert in every
 * other environment.
 */
interface ApiConfig {
  /**
   * Whether the op-class matrix denies or only records.
   *
   * Kept as reviewed code rather than an environment switch so deployments
   * cannot silently disagree about authorization. Shadow mode was used while
   * the matrix was brought up; the committed product policy is enforcement.
   */
  scopeEnforcement: ScopeEnforcementMode;
  /**
   * Explicit local test users that may exercise paid API-key minting without
   * contacting Stripe. Always empty outside development.
   */
  developmentPremiumUserIds: ReadonlySet<string>;
}

export function getDevelopmentPremiumUserIds(
  value: string | undefined,
  environment: Environment,
): ReadonlySet<string> {
  if (environment !== "development") {
    return new Set();
  }

  return new Set(
    (value ?? "")
      .split(",")
      .map((userId) => userId.trim())
      .filter(Boolean),
  );
}

/**
 * Sign in with Google (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET /
 * GOOGLE_HOSTED_DOMAINS). `null` = not configured (the default): the routes
 * report it unavailable and the dashboard shows no button.
 */
export interface GoogleAuthConfig {
  clientId: string;
  clientSecret: string;
  /** When non-empty, the ID token's `hd` must be one of these. */
  hostedDomains: ReadonlySet<string>;
}

/** Who may create an account; both sets empty = open signup. */
export interface SignupPolicy {
  allowedEmails: ReadonlySet<string>;
  allowedDomains: ReadonlySet<string>;
}

export interface AppConfig {
  api: ApiConfig;
  /** SIGNUP_ALLOWED_EMAILS / SIGNUP_ALLOWED_DOMAINS; both empty = open signup. */
  signup: SignupPolicy;
  googleAuth: GoogleAuthConfig | null;
  /**
   * AUTH_PASSWORD_ENABLED (default true). When false, password sign-in,
   * sign-up with an emailed code, password reset and email+password git
   * access are refused; accounts sign in another way (e.g. Google).
   */
  passwordAuthEnabled: boolean;
  sshProxy: SshProxyConfig;
  env: Environment;
  project: string;
  server: ServerConfig;
  analytics: AnalyticsConfig;
  logger: LoggerConfig;
  sendGrid: SendGridConfig;
  postgres: PostgresConfig;
  redis: RedisConfig;
  jwt: JwtConfig;
  favaApi: FavaAPIConfig;
  dashboard: DashboardConfig;
  appLinks: AppLinksConfig;
  mcpRegistry: McpRegistryConfig;
  gitea: GiteaConfig;
  blockeden: BlockEdenConfig;
  claudeCodeSandbox: ClaudeCodeSandboxConfig;
  /** Controls which Ask AI backend to use: "bql" (local LLM+BQL) or "sandbox" (Cloudflare sandbox proxy) */
  askAiMode: "bql" | "sandbox";
  agent: AgentConfig;
  stripe: StripeConfig;
  tempAssetS3: AssetS3Config;
  loki: LokiConfig;
  plaid: PlaidConfig;
  metricsApiToken: string;
  adminToken: string;
  oauth: OAuthConfig;
}

function getEnvironment(env: unknown): Environment {
  if (typeof env !== "string") {
    return "production";
  }
  switch (env) {
    case "development":
      return "development";
    case "test":
      return "test";
    default:
      return "production";
  }
}

export function getOAuthPublicUrl(
  value: string | undefined,
  fallback: string,
  name: string,
  env: Environment,
): string {
  const configured = value === undefined ? fallback : value.trim();
  if (!configured) throw new Error(`${name} must be a non-empty absolute URL`);

  let url: URL;
  try {
    url = new URL(configured);
  } catch {
    throw new Error(`${name} must be a non-empty absolute URL`);
  }
  if (url.username || url.password || url.search || url.hash) {
    throw new Error(`${name} must not contain credentials, query, or fragment`);
  }
  const isLoopback = ["localhost", "127.0.0.1", "::1"].includes(url.hostname);
  if (url.protocol !== "https:" && !(env !== "production" && isLoopback)) {
    throw new Error(
      `${name} must use HTTPS except on localhost in development`,
    );
  }
  return url.toString().replace(/\/$/, "");
}

/**
 * The registry's parser accepts `v=MCPv1;\s*k=<algo>;\s*p=<base64>`; we
 * require the exact spacing `mcp-publisher` emits so a value that "almost"
 * matches fails here, at startup, rather than as a generic signature error at
 * publish time.
 */
const MCP_REGISTRY_AUTH_PROOF_PATTERN =
  /^v=MCPv1; k=(ed25519|ecdsap384); p=[A-Za-z0-9+/]+={0,2}$/;

export function getMcpRegistryAuthProof(
  value: string | undefined,
): string | null {
  const record = value?.trim();
  if (!record) return null;
  if (!MCP_REGISTRY_AUTH_PROOF_PATTERN.test(record)) {
    throw new Error(
      "MCP_REGISTRY_AUTH_PROOF must be the whole proof record `v=MCPv1; k=<ed25519|ecdsap384>; p=<base64 public key>`",
    );
  }
  return record;
}

export function assertOAuthInteractionHost(
  issuer: string,
  interactionUrl: string,
): void {
  if (new URL(issuer).hostname !== new URL(interactionUrl).hostname) {
    throw new Error(
      "DASHBOARD_URL must use the issuer hostname so interaction cookies remain available",
    );
  }
}

function getPlaidEnvironment(env: unknown): PlaidEnvironment {
  if (typeof env !== "string") {
    return "sandbox";
  }
  switch (env) {
    case "sandbox":
      return "sandbox";
    case "development":
      return "development";
    case "production":
      return "production";
    default:
      return "sandbox";
  }
}

/**
 * Derive the internal Gitea base URL. Scheme comes from GITEA_PROTOCOL when
 * set, otherwise https on 443 and http elsewhere; the port suffix is omitted
 * for the scheme's default port so the URL stays canonical.
 */
function giteaInternalBaseUrl(hostname: string, port: number): string {
  const protocol =
    process.env.GITEA_PROTOCOL || (port === 443 ? "https" : "http");
  const defaultPort = protocol === "https" ? 443 : 80;
  const portSuffix = port === defaultPort ? "" : `:${port}`;
  return `${protocol}://${hostname}${portSuffix}`;
}

const giteaInternalHostname = process.env.GITEA_HOST_NAME || "gitea";
const giteaHttpPort = parseInt(process.env.GITEA_HTTP_PORT || "3000", 10);
const environment = getEnvironment(process.env.NODE_ENV);
const dashboardUrl = getOAuthPublicUrl(
  process.env.DASHBOARD_URL,
  "https://beancount.io",
  "DASHBOARD_URL",
  environment,
);
const developmentOAuthIssuer = getOAuthPublicUrl(
  process.env.SERVER_URL,
  environment === "production"
    ? "https://beancount.io"
    : "http://localhost:4104",
  "SERVER_URL",
  environment,
);
const oauthIssuer =
  environment === "production" ? dashboardUrl : developmentOAuthIssuer;
const oauthInteractionUrl = getOAuthPublicUrl(
  process.env.DASHBOARD_URL,
  environment === "production" ? dashboardUrl : "http://localhost:5173",
  "DASHBOARD_URL",
  environment,
);
assertOAuthInteractionHost(oauthIssuer, oauthInteractionUrl);
const oauthSigningKeys = getOptionalJwks(environment);

export const config: AppConfig = {
  api: {
    scopeEnforcement: "enforce",
    developmentPremiumUserIds: getDevelopmentPremiumUserIds(
      process.env.DEV_PREMIUM_USER_IDS,
      environment,
    ),
  },
  passwordAuthEnabled: parsePasswordAuthEnabled(
    process.env.AUTH_PASSWORD_ENABLED,
  ),
  googleAuth: parseGoogleAuthConfig({
    GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET: process.env.GOOGLE_CLIENT_SECRET,
    GOOGLE_HOSTED_DOMAINS: process.env.GOOGLE_HOSTED_DOMAINS,
  }),
  signup: {
    allowedEmails: parseSignupAllowedEmails(process.env.SIGNUP_ALLOWED_EMAILS),
    allowedDomains: parseSignupAllowedDomains(
      process.env.SIGNUP_ALLOWED_DOMAINS,
    ),
  },
  env: environment,
  project: "beancount-io",
  jwt: {
    secret: process.env.AUTH_SECRET || "",
    expMins: parseInt(process.env.AUTH_JWT_EXP_MINUTES || "525600", 10),
    cookieDomain: parseCookieDomain(process.env.AUTH_COOKIE_DOMAIN),
  },
  favaApi: {
    baseUrl: process.env.FAVA_API_URL || "",
    adminUser: process.env.FAVA_API_ADMIN_USER || "",
    adminPassword: process.env.FAVA_API_ADMIN_PASSWORD || "",
  },
  dashboard: {
    url: dashboardUrl,
  },
  appLinks: {
    appleTeamId: process.env.APP_LINKS_APPLE_TEAM_ID?.trim() || null,
    androidSha256Fingerprints: (process.env.APP_LINKS_ANDROID_SHA256 ?? "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
  },
  mcpRegistry: {
    authProof: getMcpRegistryAuthProof(process.env.MCP_REGISTRY_AUTH_PROOF),
  },
  gitea: {
    hostname: process.env.EXTERNAL_GITEA_HOST_NAME || "git.beancount.io",
    internalHostname: giteaInternalHostname,
    httpPort: giteaHttpPort,
    internalBaseUrl: giteaInternalBaseUrl(giteaInternalHostname, giteaHttpPort),
    externalHttpPort: parseInt(
      process.env.EXTERNAL_GITEA_HTTP_PORT || "443",
      10,
    ),
    sshPort: parseInt(process.env.GITEA_SSH_PORT || "2222", 10),
  },

  /**
   * The SSH half of the git control plane (ADR 0004). Disabled unless a host
   * key is configured: starting a listener that presents a key nobody has seen
   * would break every existing client with a host-key warning.
   */
  sshProxy: {
    enabled: process.env.SSH_PROXY_ENABLED === "true",
    port: parseInt(process.env.SSH_PROXY_PORT || "2222", 10),
    // OpenSSH private key, PEM-encoded. Must be Gitea's own host key: any
    // other key gives every prior client a host-key-changed warning that is
    // indistinguishable from an attack (ADR 0004). Retrieve it with
    // _infra/print-ssh-host-key.sh.
    hostKey: process.env.SSH_PROXY_HOST_KEY || "",
  },
  blockeden: {
    accessKey: process.env.BLOCKEDEN_ACCESS_KEY || "",
  },
  claudeCodeSandbox: {
    apiUrl: process.env.CLAUDE_CODE_SANDBOX_URL || "",
  },
  askAiMode: process.env.ASK_AI_MODE === "sandbox" ? "sandbox" : "bql",
  agent: {
    mode: process.env.AGENT_MODE === "sandbox" ? "sandbox" : "self-hosted",
    sandboxApiUrl: process.env.CLAUDE_CODE_AGENT_URL || "",
  },
  server: {
    proxy: true,
    port: parseInt(process.env.PORT || "4104", 10),
    url: process.env.SERVER_URL || "https://api.v3.beancount.io",
    corsAllowedOrigins: parseCorsAllowedOrigins(
      process.env.CORS_ALLOWED_ORIGINS,
    ),
  },
  logger: {
    enabled: true,
    level: "debug",
  },
  postgres: {
    uri: process.env.POSTGRES_BACKEND_URI || "",
  },
  redis: {
    uri: process.env.REDIS_URI || "redis://localhost:6379",
  },
  sendGrid: {
    apiKey: process.env.SEND_GRID_API_KEY || "",
  },
  analytics: {
    gaMeasurementId: "G-94TFG6X2Q5",
  },
  stripe: {
    webhookSecret: process.env.STRIPE_WEBHOOK_SECRET || "",
    publicKey: process.env.STRIPE_PUBLIC_KEY || "",
    privateKey: process.env.STRIPE_PRIVATE_KEY || "",
  },
  tempAssetS3: {
    endpoint: process.env.TEMP_ASSETS_AWS_S3_ENDPOINT || "",
    region: process.env.TEMP_ASSETS_AWS_S3_REGION || "",
    bucket: process.env.TEMP_ASSETS_AWS_S3_BUCKET || "",
    accessKeyId: process.env.TEMP_ASSETS_AWS_S3_ACCESS_KEY_ID || "",
    secretAccessKey: process.env.TEMP_ASSETS_AWS_S3_SECRET_ACCESS_KEY || "",
    uploadUrlExpiration: 300, // 5 minutes
    downloadUrlExpiration: 600, // 10 minutes
  },
  loki: {
    host: process.env.LOKI_HOST || "",
  },
  plaid: {
    clientId: process.env.PLAID_CLIENT_ID || "",
    secret: process.env.PLAID_SECRET || "",
    environment: getPlaidEnvironment(process.env.PLAID_ENVIRONMENT),
    webhookUrl: process.env.PLAID_WEBHOOK_URL || "",
  },
  metricsApiToken: process.env.METRICS_API_TOKEN || "",
  adminToken: process.env.ADMIN_TOKEN || "",
  oauth: {
    issuer: oauthIssuer,
    interactionUrl: oauthInteractionUrl,
    jwks: oauthSigningKeys.jwks,
    unavailableReason: oauthSigningKeys.unavailableReason,
    // The only client-specific deployment input. `||` (not `??`) makes empty
    // equivalent to unset, so the optional client is simply not registered.
    discourseClientSecret: process.env.OAUTH_DISCOURSE_CLIENT_SECRET || "",
  },
};
