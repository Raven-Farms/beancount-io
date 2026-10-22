/**
 * Free text for a route param, safe to push.
 *
 * `router.push` percent-encodes each param once; expo-router decodes the URL
 * once when it parses it, and the route-params hook then runs
 * `decodeURIComponent` over the value a second time. Text that happens to
 * contain `%` plus two hex digits came back as the character it spells: a
 * narration "50%50" as "50P", a file named "2024%20Q1" as "2024 Q1", which
 * opened a different file (w21/221). Escaping each `%` once more makes the
 * second decode return exactly what was sent, and leaves every string without
 * a `%` untouched.
 */
export function routeText(value: string): string;
export function routeText(value: string | undefined): string | undefined;
export function routeText(value: string | undefined): string | undefined {
  return value === undefined ? undefined : value.replace(/%/g, "%25");
}
