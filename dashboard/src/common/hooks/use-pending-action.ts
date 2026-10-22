import { useLayoutEffect, useRef, useState } from "react";

/**
 * One in-flight write at a time, with its focus handback: the core of
 * `usePendingSubmit`'s entry forms (w4/m33) and the profile dialogs (w4/m47).
 *
 * `run` starts `action` unless one is pending, and returns `null` when it
 * refuses, so a second Enter or click sends nothing. `pending` holds from the
 * start until the action settles; callers lock their fields and dismissal on
 * it, so no edit is accepted that the success would then discard and no
 * completion lands on a later draft.
 *
 * `action` resolves `true` once its write landed. Anything else — a refusal,
 * a failed request — is a failure, and the control that started it gets
 * focus back for the retry (w4/m42).
 */
export function usePendingAction() {
  const inFlight = useRef(false);
  const [pending, setPending] = useState(false);

  // The lock disables the control that started the write, and the browser
  // drops its focus; Shift+Tab from the bare dialog could reach the page
  // behind it. Park focus on the nearest focusable region around that control
  // (New Entry's tab panel, else the dialog, whose trap then holds it) until
  // the lock lifts.
  const origin = useRef<HTMLElement | null>(null);
  useLayoutEffect(() => {
    const target = origin.current;
    if (!target) return;
    const active = document.activeElement;
    // Focus that sits on the control itself or on a region around it was
    // never moved anywhere by the user.
    const lost = !active || active.contains(target);
    if (pending) {
      if (lost && target.matches(":disabled")) {
        target.parentElement
          ?.closest<HTMLElement>("[tabindex]")
          ?.focus({ preventScroll: true });
      }
      return;
    }
    origin.current = null;
    if (lost && target.isConnected) target.focus();
  }, [pending]);

  const run = (action: () => Promise<boolean | void>) => {
    if (inFlight.current) return null;
    inFlight.current = true;
    origin.current =
      document.activeElement instanceof HTMLElement &&
      document.activeElement !== document.body
        ? document.activeElement
        : null;
    setPending(true);
    return (async () => {
      try {
        // A landed write gets no handback: closing the dialog places focus.
        if ((await action()) === true) origin.current = null;
      } finally {
        inFlight.current = false;
        setPending(false);
      }
    })();
  };

  return { run, pending };
}
