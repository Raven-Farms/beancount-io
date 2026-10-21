/**
 * Keep an amount in left-to-right order inside a translated sentence. In a
 * right-to-left line the first Persian letter sets the direction, and the
 * `-`, `+` and `$` around a number are neutral, so "مانده: -$1,234.50"
 * rendered as `1,234.50$- :مانده` (w21/095). A left-to-right isolate
 * (U+2066 … U+2069) is the plain-text form of the dashboard's `<bdi dir=ltr>`
 * (w3/479); in a left-to-right sentence it changes nothing visible.
 *
 * Free of `@/` value imports so the jest-lite runner can require it.
 */
export function isolateLtr(text: string): string {
  return `⁦${text}⁩`;
}
