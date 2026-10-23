/**
 * Whether Delete Account's typed confirmation may be confirmed: the phrase,
 * ignoring surrounding spaces (an iOS suggestion appends one), or else why
 * not. Matched exactly, a trailing space left Delete greyed out with nothing
 * saying why (w21/158). Empty text disables without a message.
 */
export function deleteConfirmationCheck(
  text: string,
  phrase: string,
  mismatch: string,
): true | false | string {
  const typed = text.trim();
  if (typed === phrase) return true;
  return typed ? mismatch : false;
}
