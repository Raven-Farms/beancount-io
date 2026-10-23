import { useCallback, useEffect, useRef } from "react";
import { useNavigation } from "expo-router";

/**
 * Whether the screen that called this is still the one the user is on, read
 * at the moment it is asked. Post-write navigation used to run when the write
 * landed, wherever the user had gone meanwhile: expo-router's `router` is
 * global, so `back()` or `dismiss(2)` closed whatever screen was now on top
 * (w21/194). A write that finishes after the user left only needs its toast.
 */
export function useIsHere(): () => boolean {
  const navigation = useNavigation();
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  return useCallback(
    () => mounted.current && navigation.isFocused(),
    [navigation],
  );
}
