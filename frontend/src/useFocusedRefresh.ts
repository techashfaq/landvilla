import { useFocusEffect } from "expo-router";
import { useCallback } from "react";
import { AppState } from "react-native";

/** Keep private screens current only while visible, including returning from background. */
export function useFocusedRefresh(refresh: () => Promise<unknown>, enabled: boolean) {
  useFocusEffect(useCallback(() => {
    if (!enabled) return;
    void refresh();
    const subscription = AppState.addEventListener("change", state => { if (state === "active") void refresh(); });
    return () => subscription.remove();
  }, [enabled, refresh]));
}
