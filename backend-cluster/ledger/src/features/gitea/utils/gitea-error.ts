/**
 * Read the HTTP status off an error thrown by the generated Gitea client. The
 * client throws the failed HttpResponse (a Response subclass) on non-2xx.
 */
export function giteaErrorStatus(error: unknown): number | undefined {
  if (error && typeof error === "object" && "status" in error) {
    const status = (error as { status?: unknown }).status;
    if (typeof status === "number") return status;
  }
  return undefined;
}

/** Whether a thrown Gitea error is a 404 Not Found. */
export function isGiteaNotFound(error: unknown): boolean {
  return giteaErrorStatus(error) === 404;
}

/** Best-effort human-readable message from a generated Gitea HttpResponse. */
export function giteaErrorMessage(error: unknown): string {
  if (!error || typeof error !== "object") return String(error ?? "");
  const response = error as {
    error?: unknown;
    message?: unknown;
    statusText?: unknown;
  };
  if (response.error && typeof response.error === "object") {
    const message = (response.error as { message?: unknown }).message;
    if (typeof message === "string") return message;
  }
  if (typeof response.error === "string") return response.error;
  if (typeof response.message === "string") return response.message;
  if (typeof response.statusText === "string" && response.statusText) {
    return response.statusText;
  }
  const status = giteaErrorStatus(error);
  return status === undefined ? "" : `Gitea request failed with HTTP ${status}`;
}

/**
 * Gitea messages that mean a write lost an optimistic-concurrency race.
 */
const CONFLICT_MESSAGE_RE =
  /sha does not match|already exists?|not up to date/iu;

/** The one 400 that is a lost race: the delete's stale sha. */
const STALE_SHA_RE = /sha does not match/iu;

/**
 * How Gitea answers the loser of two commits racing for the branch ref: the
 * contents API does not map the push failure, so it is a 500 whose message is
 * the git error — observed on Gitea 1.24.7 as `PushRejected Error: … cannot
 * lock ref 'refs/heads/main': is at X but expected Y` (w23/017). An
 * out-of-date push is the same race lost later. Other push rejections (a hook
 * declining the commit) are not races and are not matched.
 */
const LOST_REF_RACE_RE = /cannot lock ref|PushOutOfDate/u;

export function isGiteaWriteConflict(error: unknown): boolean {
  const status = giteaErrorStatus(error);
  if (status === 409) return true;
  if (status === 422) return CONFLICT_MESSAGE_RE.test(giteaErrorMessage(error));
  // Gitea 1.24 answers a stale sha on the single-file delete with 400, not the
  // 422 the update and create routes use (w21/550). Other 400s are bad input.
  if (status === 400) return STALE_SHA_RE.test(giteaErrorMessage(error));
  if (status === 500) return LOST_REF_RACE_RE.test(giteaErrorMessage(error));
  return false;
}
