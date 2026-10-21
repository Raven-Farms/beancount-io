/**
 * A screen holding unsaved edits that something other than navigation could
 * throw away. An app link to another ledger switches `ledgerVar` before it
 * navigates, which remounts the file editor clean, so its `beforeRemove`
 * guard never saw the draft it discarded (w21/090). The editor registers a
 * check here while it is dirty; the link asks it first.
 *
 * Free of `@/` value imports so the jest-lite runner can require it.
 */
type UnsavedEditsCheck = () => Promise<boolean>;

let active: UnsavedEditsCheck | null = null;

/**
 * Register `check`, which asks the user and resolves true to discard the
 * edits and go on, false to stay. Returns the unregister function.
 */
export function registerUnsavedEditsGuard(
  check: UnsavedEditsCheck,
): () => void {
  active = check;
  return () => {
    if (active === check) active = null;
  };
}

/** Whether it is fine to throw away the active screen's unsaved edits. */
export function confirmDiscardUnsavedEdits(): Promise<boolean> {
  return active ? active() : Promise.resolve(true);
}
