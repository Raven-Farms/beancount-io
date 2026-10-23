export const OFFICIAL_SERVER_URL = "https://beancount.io/";

export type ServerUrlErrorCode =
  "empty" | "invalid" | "credentials" | "query" | "insecure";

export type ServerUrlValidation =
  { ok: true; url: string } | { ok: false; code: ServerUrlErrorCode };

type ServerUrlOptions = {
  allowInsecureLocalhost?: boolean;
};

const localhostNames = new Set(["localhost", "127.0.0.1", "::1"]);

export function allowsInsecureLocalhost(): boolean {
  return typeof __DEV__ !== "undefined" && __DEV__;
}

function isLocalhost(hostname: string): boolean {
  // URL brackets an IPv6 literal in `hostname` (`[::1]`); the set holds names.
  const host = hostname.toLowerCase().replace(/^\[(.+)\]$/u, "$1");
  return localhostNames.has(host);
}

const PUNYCODE_BASE = 36;
const PUNYCODE_T_MIN = 1;
const PUNYCODE_T_MAX = 26;
const PUNYCODE_SKEW = 38;
const PUNYCODE_DAMP = 700;
const PUNYCODE_INITIAL_BIAS = 72;
const PUNYCODE_INITIAL_N = 128;

function punycodeDigit(value: number): string {
  return String.fromCharCode(value < 26 ? value + 97 : value + 22);
}

function punycodeAdapt(delta: number, points: number, first: boolean): number {
  let scaled = first ? Math.floor(delta / PUNYCODE_DAMP) : delta >> 1;
  scaled += Math.floor(scaled / points);
  let k = 0;
  while (scaled > ((PUNYCODE_BASE - PUNYCODE_T_MIN) * PUNYCODE_T_MAX) >> 1) {
    scaled = Math.floor(scaled / (PUNYCODE_BASE - PUNYCODE_T_MIN));
    k += PUNYCODE_BASE;
  }
  return (
    k +
    Math.floor(
      ((PUNYCODE_BASE - PUNYCODE_T_MIN + 1) * scaled) /
        (scaled + PUNYCODE_SKEW),
    )
  );
}

/** RFC 3492 encoding of one label's code points. */
function punycodeEncode(label: string): string {
  const input = Array.from(label, (char) => char.codePointAt(0) as number);
  let output = input
    .filter((point) => point < 0x80)
    .map((point) => String.fromCharCode(point))
    .join("");
  const basicCount = output.length;
  let handled = basicCount;
  if (basicCount > 0) output += "-";
  let n = PUNYCODE_INITIAL_N;
  let delta = 0;
  let bias = PUNYCODE_INITIAL_BIAS;
  while (handled < input.length) {
    const next = Math.min(...input.filter((point) => point >= n));
    delta += (next - n) * (handled + 1);
    n = next;
    for (const point of input) {
      if (point < n) delta += 1;
      if (point !== n) continue;
      let q = delta;
      for (let k = PUNYCODE_BASE; ; k += PUNYCODE_BASE) {
        const t =
          k <= bias
            ? PUNYCODE_T_MIN
            : k >= bias + PUNYCODE_T_MAX
              ? PUNYCODE_T_MAX
              : k - bias;
        if (q < t) break;
        output += punycodeDigit(t + ((q - t) % (PUNYCODE_BASE - t)));
        q = Math.floor((q - t) / (PUNYCODE_BASE - t));
      }
      output += punycodeDigit(q);
      bias = punycodeAdapt(delta, handled + 1, handled === basicCount);
      delta = 0;
      handled += 1;
    }
    delta += 1;
    n += 1;
  }
  return output;
}

/**
 * A host in the ASCII form the backend's issuer uses. React Native's URL
 * polyfill keeps a Unicode host as typed (no punycode), so `bücher.example`
 * never matched an issuer of `xn--bcher-kva.example` (w21/216). A trailing dot
 * names the same host and is dropped, so it cannot make a second override.
 */
export function asciiHost(hostname: string): string {
  const host = hostname.replace(/\.+$/, "");
  // eslint-disable-next-line no-control-regex
  if (/^[\x00-\x7f]*$/.test(host)) return host.toLowerCase();
  let folded = host;
  try {
    folded = host.normalize("NFKC").toLowerCase();
  } catch {
    folded = host.toLowerCase();
  }
  return folded
    .split(/[.\u3002\uff0e\uff61]/)
    .map((label) =>
      // eslint-disable-next-line no-control-regex
      /^[\x00-\x7f]*$/.test(label) ? label : `xn--${punycodeEncode(label)}`,
    )
    .join(".");
}

/** Validate a base URL while preserving a reverse-proxy path prefix. */
export function validateServerUrl(
  input: string,
  options: ServerUrlOptions = {},
): ServerUrlValidation {
  const candidate = input.trim();
  if (!candidate) return { ok: false, code: "empty" };

  let parsed: URL;
  try {
    parsed = new URL(candidate);
  } catch {
    return { ok: false, code: "invalid" };
  }
  if (
    !parsed.hostname ||
    (parsed.protocol !== "https:" && parsed.protocol !== "http:")
  ) {
    return { ok: false, code: "invalid" };
  }
  if (parsed.username || parsed.password) {
    return { ok: false, code: "credentials" };
  }
  if (parsed.search || parsed.hash) return { ok: false, code: "query" };

  const allowHttp = options.allowInsecureLocalhost ?? allowsInsecureLocalhost();
  if (
    parsed.protocol === "http:" &&
    !(allowHttp && isLocalhost(parsed.hostname))
  ) {
    return { ok: false, code: "insecure" };
  }

  const pathname = `${parsed.pathname.replace(/\/+$/, "")}/`;
  const host = asciiHost(parsed.hostname);
  // Spelled out only when the host changed; an IPv6 literal keeps its brackets.
  const url =
    host === parsed.hostname
      ? (() => {
          parsed.pathname = pathname;
          parsed.search = "";
          parsed.hash = "";
          return parsed.toString();
        })()
      : `${parsed.protocol}//${host}${parsed.port ? `:${parsed.port}` : ""}${pathname}`;
  // An empty "?" or "#" survives in the string form but names nothing: it made
  // `https://beancount.io/?` a second override that was not the default.
  return { ok: true, url: url.replace(/[?#]+$/, "") };
}

export function endpointFor(serverUrl: string, path: string): string {
  return new URL(path.replace(/^\/+/, ""), serverUrl).toString();
}

/** The hosted preview catalog is only available at the official root endpoint. */
export function isOfficialServerUrl(input: string): boolean {
  const result = validateServerUrl(input);
  return result.ok && result.url === OFFICIAL_SERVER_URL;
}
