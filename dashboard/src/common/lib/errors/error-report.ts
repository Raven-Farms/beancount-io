const MAX_STACK_LINES = 20;
const MAX_URL_LENGTH = 8192;
const REDACTED = "[REDACTED]";
const RECOVERY_CHALLENGE = /\brcv_[a-f0-9]{64}\b/gi;
const AUTH_KEY =
  "recovery|challenge[_-]?id|(?:one[_-]?time|access|refresh|id|reset|session|email|auth)?[_-]?token|code|code[_-]?verifier|password|client[_-]?secret|state|api[_-]?key|email|authorization";
const AUTH_PARAMETER = new RegExp(`^(?:${AUTH_KEY})$`, "i");
const LABELLED_CREDENTIAL = new RegExp(
  `(\\b(?:${AUTH_KEY})\\b["']?\\s*[:=]\\s*)(?:Bearer\\s+)?(?:"[^"\\r\\n]*"|'[^'\\r\\n]*'|\\[REDACTED\\]|[^\\s&;,}\\]\\)]+)`,
  "gi",
);

function diagnosticLocation(raw: string): {
  url: string;
  secrets: Set<string>;
} {
  const secrets = new Set<string>();
  if (!raw) return { url: "", secrets };
  if (raw.length > MAX_URL_LENGTH) return { url: "[unavailable]", secrets };
  try {
    const parsed = new URL(raw);
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:")
      return { url: "[unavailable]", secrets };
    for (const value of [parsed.username, parsed.password]) {
      if (!value) continue;
      secrets.add(value);
      try {
        secrets.add(decodeURIComponent(value));
      } catch {
        // Malformed userinfo must not prevent masking other URL credentials.
      }
    }
    // Support both #token=... and hash-router #/callback?token=... links.
    const fragment = parsed.hash.slice(1);
    const fragmentQuery = fragment.slice(fragment.indexOf("?") + 1);
    for (const params of [
      parsed.searchParams,
      new URLSearchParams(fragmentQuery),
    ]) {
      for (const [key, value] of params) {
        if (value && AUTH_PARAMETER.test(key)) secrets.add(value);
      }
    }
    return { url: `${parsed.origin}${parsed.pathname}`, secrets };
  } catch {
    return { url: "[unavailable]", secrets };
  }
}

function redactCredentials(secrets: Set<string>): (text: string) => string {
  const echoes = new Set<string>();
  for (const value of secrets) {
    echoes.add(value);
    echoes.add(encodeURIComponent(value));
    echoes.add(new URLSearchParams({ value }).toString().slice(6));
  }
  // Literal alternatives, longest first; a single pass also avoids replacing
  // parts of our own redaction marker when a credential is unusually short.
  const echoedCredential = echoes.size
    ? new RegExp(
        [...echoes]
          .sort((a, b) => b.length - a.length)
          .map((value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
          .join("|"),
        "gi",
      )
    : undefined;
  return (text) => {
    const masked = echoedCredential
      ? text.replace(echoedCredential, REDACTED)
      : text;
    return masked
      .replace(LABELLED_CREDENTIAL, `$1${REDACTED}`)
      .replace(RECOVERY_CHALLENGE, REDACTED);
  };
}

function firstLines(text: string | null | undefined): string {
  if (!text) return "";
  const lines = text.trim().split("\n");
  const kept = lines.slice(0, MAX_STACK_LINES);
  if (lines.length > kept.length) kept.push("…");
  return kept.join("\n");
}

interface ErrorReportInput {
  error: unknown;
  componentStack?: string | null;
  url: string;
  userAgent: string;
  time: Date;
}

/**
 * Plain-text report a reader can copy to support. It carries what identifies
 * the failure — the error, where and when it happened, and the browser — and
 * nothing from the session: no cookies, tokens, or request variables.
 */
export function formatErrorReport({
  error,
  componentStack,
  url,
  userAgent,
  time,
}: ErrorReportInput): string {
  const location = diagnosticLocation(url);
  const redact = redactCredentials(location.secrets);
  const name = redact(error instanceof Error ? error.name : "Error");
  const message = redact(
    error instanceof Error ? error.message : String(error),
  );
  // Redact complete values before line truncation can split a credential.
  const stack =
    error instanceof Error ? firstLines(redact(error.stack ?? "")) : "";
  const components = firstLines(redact(componentStack ?? ""));

  return [
    `${name}: ${message}`,
    `URL: ${location.url.replace(RECOVERY_CHALLENGE, REDACTED)}`,
    `Time: ${time.toISOString()}`,
    `Browser: ${redact(userAgent)}`,
    stack && `\nStack:\n${stack}`,
    components && `\nComponents:\n${components}`,
  ]
    .filter(Boolean)
    .join("\n");
}
