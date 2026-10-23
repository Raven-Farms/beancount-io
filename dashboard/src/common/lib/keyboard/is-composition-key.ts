/**
 * A key event an input method is consuming (w4/286): its Enter confirms the
 * composed text and its arrows pick candidates, so app shortcuts must leave
 * it alone. keyCode 229 is how some engines report such a key.
 */
export function isCompositionKey(event: KeyboardEvent): boolean {
  return event.isComposing || event.keyCode === 229;
}
