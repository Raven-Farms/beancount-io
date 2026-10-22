import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type BaseSyntheticEvent,
} from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";

/**
 * One in-flight submission per entry form: New Entry's (w4/m33) and Accounts'
 * Open Account (w4/284).
 *
 * react-hook-form runs every `handleSubmit` call it is given, so a disabled
 * button alone does not stop Cmd/Ctrl+Enter or a second Enter from sending
 * the entry again. `submit` refuses while a write is pending, and `pending`
 * locks the form's fields so no edit is accepted that the success reset would
 * then discard. The lock lifts when the write settles, success or failure;
 * a failure keeps the draft for a retry. `onPendingChange` lets the dialog
 * hold its tabs and dismissal for the same window.
 *
 * `onValid` resolves `true` once the entry is written. Anything else — a
 * refusal, a failed request — is a failure, and the control that submitted
 * gets focus back for the retry (w4/m42).
 */
export function usePendingSubmit<T extends FieldValues>(
  form: UseFormReturn<T>,
  onValid: (data: T) => Promise<boolean | void>,
  onPendingChange?: (pending: boolean) => void,
) {
  const inFlight = useRef(false);
  const [pending, setPending] = useState(false);

  const reportPending = useRef(onPendingChange);
  useEffect(() => {
    reportPending.current = onPendingChange;
  }, [onPendingChange]);
  useEffect(() => {
    reportPending.current?.(pending);
  }, [pending]);
  // A form that unmounts mid-write must not leave its dialog locked.
  useEffect(() => () => reportPending.current?.(false), []);

  // The lock disables the control that submitted, and the browser drops its
  // focus; Shift+Tab from the bare dialog could reach the page behind it. Park
  // focus on the nearest focusable region around that control (New Entry's
  // tab panel, else the dialog, whose trap then holds it) until the lock lifts.
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

  const submit = async (event?: BaseSyntheticEvent) => {
    if (inFlight.current) {
      event?.preventDefault();
      return;
    }
    inFlight.current = true;
    origin.current =
      document.activeElement instanceof HTMLElement &&
      document.activeElement !== document.body
        ? document.activeElement
        : null;
    setPending(true);
    try {
      await form.handleSubmit(async (data) => {
        // A written entry gets no handback: closing the dialog places focus.
        if ((await onValid(data)) === true) origin.current = null;
      })(event);
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  };

  return { submit, pending };
}
