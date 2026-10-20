import { useEffect, useRef, useState, type BaseSyntheticEvent } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";

/**
 * One in-flight submission per New Entry form (w4/m33).
 *
 * react-hook-form runs every `handleSubmit` call it is given, so a disabled
 * button alone does not stop Cmd/Ctrl+Enter or a second Enter from sending
 * the entry again. `submit` refuses while a write is pending, and `pending`
 * locks the form's fields so no edit is accepted that the success reset would
 * then discard. The lock lifts when the write settles, success or failure;
 * a failure keeps the draft for a retry. `onPendingChange` lets the dialog
 * hold its tabs and dismissal for the same window.
 */
export function usePendingSubmit<T extends FieldValues>(
  form: UseFormReturn<T>,
  onValid: (data: T) => Promise<void>,
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

  // Locking the fields drops focus from the one being typed in; hand it back
  // once they are enabled again, unless something else (a closing dialog)
  // has taken focus meanwhile.
  const focusBefore = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (pending) return;
    const target = focusBefore.current;
    focusBefore.current = null;
    if (
      target?.isConnected &&
      (document.activeElement === null ||
        document.activeElement === document.body)
    ) {
      target.focus();
    }
  }, [pending]);

  const submit = async (event?: BaseSyntheticEvent) => {
    if (inFlight.current) {
      event?.preventDefault();
      return;
    }
    inFlight.current = true;
    focusBefore.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    setPending(true);
    try {
      await form.handleSubmit(onValid)(event);
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  };

  return { submit, pending };
}
