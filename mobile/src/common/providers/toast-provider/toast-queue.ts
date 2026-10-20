export type ToastType = "success" | "error" | "text" | "loading";

export interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

/** How long a toast stays up when its caller does not say. */
export const DEFAULT_TOAST_DURATION = 2000;

/** The longest an error toast stays up to be read (w21/001). */
export const MAX_ERROR_TOAST_DURATION = 8000;

/**
 * A missing (or zero) duration falls back to the default, and an error toast
 * gets reading time on top — about 60 ms a character, capped — so a
 * sentence-long refusal is still up when the user gets to its end (w21/001).
 */
export const toastDuration = (message: Omit<ToastMessage, "id">): number =>
  message.duration ||
  (message.type === "error"
    ? Math.min(
        MAX_ERROR_TOAST_DURATION,
        DEFAULT_TOAST_DURATION + 60 * message.message.length,
      )
    : DEFAULT_TOAST_DURATION);

/** Queue a toast after the ones already showing. */
export const withToast = (
  messages: ToastMessage[],
  message: ToastMessage,
): ToastMessage[] => [...messages, message];

/** Dismiss one toast, leaving the rest in order. */
export const withoutToast = (
  messages: ToastMessage[],
  id: string,
): ToastMessage[] => messages.filter((message) => message.id !== id);

/**
 * The toast context a component reads, or an error when none is mounted. The
 * context defaults to null so a component rendered outside `ToastProvider`
 * fails loudly instead of receiving a `showToast` that silently does nothing.
 */
export function requireToastContext<T>(context: T | null): T {
  if (context === null) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
