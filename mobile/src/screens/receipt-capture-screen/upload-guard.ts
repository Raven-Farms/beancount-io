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
