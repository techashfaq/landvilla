import { Ionicons } from "@react-native-vector-icons/ionicons";
import React, { createContext, useCallback, useContext, useRef, useState } from "react";
import { Text } from "react-native";
import Animated, { FadeInUp, FadeOutUp } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { fonts, makeStyles, useTheme } from "@/src/theme";

type ToastT = { msg: string; kind: "success" | "error" | "info" };
const ToastCtx = createContext<{ show: (msg: string, kind?: ToastT["kind"]) => void; toast: ToastT | null }>({ show: () => {}, toast: null });

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = useState<ToastT | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback((msg: string, kind: ToastT["kind"] = "info") => {
    if (timer.current) clearTimeout(timer.current);
    setToast({ msg, kind });
    timer.current = setTimeout(() => setToast(null), 3000);
  }, []);

  return (
    <ToastCtx.Provider value={{ show, toast }}>
      {children}
      <ToastView />
    </ToastCtx.Provider>
  );
}

/** Renders the current toast. Also mounted inside modals/sheets so toasts stay above their backdrop. */
export function ToastView() {
  const { toast } = useContext(ToastCtx);
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  if (!toast) return null;
  const bg = toast.kind === "success" ? colors.success : toast.kind === "error" ? colors.error : colors.surfaceInverse;
  const icon = toast.kind === "success" ? "checkmark-circle" : toast.kind === "error" ? "alert-circle" : "information-circle";
  return (
    <Animated.View
      entering={FadeInUp}
      exiting={FadeOutUp}
      pointerEvents="none"
      testID="toast-message"
      style={[styles.toast, { top: insets.top + 8, backgroundColor: bg }]}
    >
      <Ionicons name={icon} size={20} color={colors.onSurfaceInverse} />
      <Text style={styles.text}>{toast.msg}</Text>
    </Animated.View>
  );
}

export const useToast = () => useContext(ToastCtx);

const useStyles = makeStyles((c) => ({
  toast: {
    position: "absolute",
    left: 16,
    right: 16,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    zIndex: 1000,
    elevation: 10,
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
  },
  text: { color: c.onSurfaceInverse, fontFamily: fonts.textMedium, fontSize: 14, flex: 1 },
}));
