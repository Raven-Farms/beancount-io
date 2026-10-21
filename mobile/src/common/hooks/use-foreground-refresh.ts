import { useEffect } from "react";
import { AppState } from "react-native";
import { useApolloClient } from "@apollo/client";
import { createForegroundRefresher } from "@/common/apollo/foreground-refresh";

/**
 * Refetch every query on screen when the app returns to the foreground, so a
 * mounted tab catches up with changes made elsewhere (w21/024). Cached data
 * stays on screen while the network answers; an offline return keeps it.
 */
export function useForegroundRefresh(enabled: boolean): void {
  const client = useApolloClient();
  useEffect(() => {
    if (!enabled) return undefined;
    const onChange = createForegroundRefresher({
      refresh: () => {
        void client
          .refetchQueries({ include: "active" })
          .catch(() => undefined);
      },
    });
    const subscription = AppState.addEventListener("change", onChange);
    return () => subscription.remove();
  }, [client, enabled]);
}
