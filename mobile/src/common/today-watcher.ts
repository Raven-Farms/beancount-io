/**
 * The local calendar day, kept current while the app stays mounted. Tabs never
 * unmount, so a "today" captured once froze relative filters (1M, 3M, YTD)
 * and the price-staleness checks at the day the screen first rendered, until
 * the user reopened the filters or relaunched (w21/078).
 *
 * Free of `@/` value imports so the jest-lite runner can require it.
 */
import { getFormatDate } from "./format-util";

/** Milliseconds from `now` to the next local midnight. */
export function msUntilNextLocalMidnight(now: Date): number {
  const next = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  return next.getTime() - now.getTime();
}

/**
 * Report the day whenever it may have changed: on a return to the
 * foreground, and when the midnight timer fires. `onDay` is called only when
 * the `YYYY-MM-DD` actually differs from the last one reported.
 */
export function createTodayWatcher({
  now = () => new Date(),
  onDay,
}: {
  now?: () => Date;
  onDay: (day: string) => void;
}) {
  let day = getFormatDate(now());
  const check = () => {
    const current = getFormatDate(now());
    if (current !== day) {
      day = current;
      onDay(current);
    }
  };
  return {
    today: () => day,
    onAppStateChange: (status: string) => {
      if (status === "active") check();
    },
    onMidnight: check,
  };
}
