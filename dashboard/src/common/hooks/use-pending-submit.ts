import { useEffect, useRef, type BaseSyntheticEvent } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { usePendingAction } from "./use-pending-action";

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
  const { run, pending } = usePendingAction();

  const reportPending = useRef(onPendingChange);
  useEffect(() => {
    reportPending.current = onPendingChange;
  }, [onPendingChange]);
  useEffect(() => {
    reportPending.current?.(pending);
  }, [pending]);
  // A form that unmounts mid-write must not leave its dialog locked.
  useEffect(() => () => reportPending.current?.(false), []);

  const submit = async (event?: BaseSyntheticEvent) => {
    const submitting = run(async () => {
      let written: boolean | void = false;
      await form.handleSubmit(async (data) => {
        written = await onValid(data);
      })(event);
      return written;
    });
    if (!submitting) event?.preventDefault();
    await submitting;
  };

  return { submit, pending };
}
