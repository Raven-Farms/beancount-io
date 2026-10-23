import { useEffect, useState } from "react";
import { AppState } from "react-native";
import { getFormatDate } from "@/common/format-util";
import {
  createTodayWatcher,
  msUntilNextLocalMidnight,
} from "@/common/today-watcher";

/**
 * Today as a ledger date (`YYYY-MM-DD`), advancing at local midnight and when
 * the app returns to the foreground, so a screen kept mounted for days still
 * judges "today" correctly (w21/078). Memoise on it rather than on mount.
 */
export function useToday(): string {
  const [today, setToday] = useState(() => getFormatDate(new Date()));
  useEffect(() => {
    const watcher = createTodayWatcher({ onDay: setToday });
    // The day may have turned between the first render and this effect.
    setToday(watcher.today());
    let timer: ReturnType<typeof setTimeout>;
    const arm = () => {
      timer = setTimeout(
        () => {
          watcher.onMidnight();
          arm();
        },
        msUntilNextLocalMidnight(new Date()) + 1_000,
      );
    };
    arm();
    const subscription = AppState.addEventListener(
      "change",
      watcher.onAppStateChange,
    );
    return () => {
      clearTimeout(timer);
      subscription.remove();
    };
  }, []);
  return today;
}
