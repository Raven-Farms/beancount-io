/**
 * Calls `onIdle` once if `touch` is not called again within `ms`: the limit on
 * a receipt upload is silence, not duration, so a slow link that keeps moving
 * bytes is never cut off (w21/205). `stop` disarms it.
 */
export const createIdleGuard = (ms: number, onIdle: () => void) => {
  let timer: ReturnType<typeof setTimeout> | null = null;
  const stop = () => {
    if (timer) clearTimeout(timer);
    timer = null;
  };
  const touch = () => {
    stop();
    timer = setTimeout(() => {
      timer = null;
      onIdle();
    }, ms);
  };
  return { touch, stop };
};

/**
 * How an upload ended. A finished 2xx wins over the idle flag: iOS's background
 * session keeps uploading while JS is suspended, and on return the overdue idle
 * timer could fire before the completion event, so a photo that reached S3 was
 * thrown away as "upload_s3_timeout" and uploaded again (w21/636).
 */
export const uploadOutcome = (
  result: { status: number } | null | undefined,
  timedOut: boolean,
): "ok" | "timeout" | "failed" => {
  if (result && result.status >= 200 && result.status < 300) return "ok";
  return timedOut ? "timeout" : "failed";
};

/** Whole-percent progress of an upload, or `null` while the size is unknown. */
export const uploadPercent = (progress: {
  totalBytesSent: number;
  totalBytesExpectedToSend: number;
}): number | null => {
  const { totalBytesSent, totalBytesExpectedToSend } = progress;
  if (!(totalBytesExpectedToSend > 0)) return null;
  return Math.min(
    100,
    Math.max(0, Math.floor((totalBytesSent / totalBytesExpectedToSend) * 100)),
  );
};

/** One run of the receipt workflow. */
export type ReceiptAttempt = {
  cancelled: boolean;
  abort: AbortController;
  upload: { cancelAsync: () => Promise<void> } | null;
};

/**
 * Abandon an attempt: its late results and errors are ignored, and the request
 * and the transfer in flight are aborted. The busy overlay's Cancel does it
 * (w21/205), and so does leaving the screen: on Android, hardware Back popped
 * the modal while the upload and the AI parse ran on, spending receipt quota
 * on a scan no form opened for (w21/638).
 */
export function abandonAttempt(run: ReceiptAttempt | null): void {
  if (!run) return;
  run.cancelled = true;
  run.abort.abort();
  void run.upload?.cancelAsync().catch(() => undefined);
}
