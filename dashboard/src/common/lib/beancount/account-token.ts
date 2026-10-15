/**
 * Beancount account names are colon-separated components with no spaces.
 * Each component starts with an uppercase letter, caseless letter, or digit,
 * then letters, digits, or hyphens — matching the live Open Account controls
 * (hyphenated, numeric, and accented names) while rejecting empty segments,
 * whitespace, and lowercase-leading Latin components like `Assets:checking`.
 */
const ACCOUNT_COMPONENT = /^[\p{Lu}\p{Lo}\p{Nd}][\p{L}\p{Nd}-]*$/u;

/** Why a name is not a complete account token (w0/017). */
export type AccountTokenProblem =
  | { kind: "incomplete" }
  | { kind: "whitespace" }
  | { kind: "empty-component" }
  | { kind: "component-start"; component: string }
  | { kind: "invalid-character"; component: string };

const COMPONENT_START = /^[\p{Lu}\p{Lo}\p{Nd}]/u;

/**
 * The first reason `account` is not a complete account token, or `null` when
 * it is one. Lets forms say *why* — a lowercase `Assets:bank` was once told to
 * remove spaces and empty parts it never had.
 */
export function accountTokenProblem(
  account: string,
): AccountTokenProblem | null {
  if (account.length === 0) return { kind: "incomplete" };
  if (/\s/.test(account)) return { kind: "whitespace" };
  const parts = account.split(":");
  if (parts.length < 2) return { kind: "incomplete" };
  if (parts.some((part) => part.length === 0)) {
    return { kind: "empty-component" };
  }
  for (const component of parts) {
    if (ACCOUNT_COMPONENT.test(component)) continue;
    return COMPONENT_START.test(component)
      ? { kind: "invalid-character", component }
      : { kind: "component-start", component };
  }
  return null;
}

export function isCompleteAccountToken(account: string): boolean {
  return accountTokenProblem(account) === null;
}
