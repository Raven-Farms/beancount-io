import { useMemo } from "react";
import { useLocalSearchParams } from "expo-router";
import { firstParams } from "@/common/route-ledger";

/**
 * `useLocalSearchParams` with every param a plain string. Use this, not the
 * expo-router hook, for a route a link can reach: a repeated query parameter
 * arrives as an array there, and calling `.split` on it crashed the screen
 * (w21/198).
 */
export function useRouteParams<
  T extends Record<string, string | undefined>,
>(): T {
  const params = useLocalSearchParams<Record<string, string | string[]>>();
  return useMemo(() => firstParams<T>(params), [params]);
}
