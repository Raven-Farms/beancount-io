/**
 * Waits for `promise` for at most `ms`. A rejection inside the window
 * propagates; a promise still pending when it closes answers "timeout" and is
 * left running for the caller to keep watching. Import-free so the unit runner
 * can load it.
 */
export async function settleWithin<T>(
  promise: Promise<T>,
  ms: number,
): Promise<{ status: "done"; value: T } | { status: "timeout" }> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      promise.then((value) => ({ status: "done" as const, value })),
      new Promise<{ status: "timeout" }>((resolve) => {
        timer = setTimeout(() => resolve({ status: "timeout" }), ms);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}
