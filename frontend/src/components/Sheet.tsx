import { Ionicons } from "@react-native-vector-icons/ionicons";
import React from "react";
import { Modal, Platform, Pressable, Text, View } from "react-native";
import { KeyboardAvoidingView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ToastView } from "@/src/components/Toast";
import { fonts, makeStyles, useTheme } from "@/src/theme";

type Props = {
  visible: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  testID?: string;
};

export function Sheet({ visible, onClose, title, children, footer, testID }: Props) {
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose} statusBarTranslucent>
      <View style={styles.wrap}>
        <Pressable style={styles.backdrop} onPress={onClose} testID={`${testID}-backdrop`} />
        <KeyboardAvoidingView behavior={Platform.OS === "web" ? undefined : "padding"} style={styles.kav}>
          <View style={styles.sheet} testID={testID}>
            <View style={styles.handle} />
            <View style={styles.header}>
              <Text style={styles.title}>{title}</Text>
              <Pressable onPress={onClose} hitSlop={12} style={styles.close} testID={`${testID}-close`}>
                <Ionicons name="close" size={22} color={colors.onSurface} />
              </Pressable>
            </View>
            {children}
            {footer && <View style={[styles.footer, { paddingBottom: insets.bottom + 16 }]}>{footer}</View>}
          </View>
        </KeyboardAvoidingView>
        <ToastView />
      </View>
    </Modal>
  );
}

const useStyles = makeStyles((c) => ({
  wrap: { flex: 1, justifyContent: "flex-end" },
  backdrop: { ...({ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 } as const), backgroundColor: "rgba(28,25,23,0.45)" },
  kav: { width: "100%", maxHeight: "92%" },
  sheet: { backgroundColor: c.surface, borderTopLeftRadius: 20, borderTopRightRadius: 20, overflow: "hidden" },
  handle: { alignSelf: "center", width: 40, height: 4, borderRadius: 2, backgroundColor: c.borderStrong, marginTop: 8 },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 16, paddingVertical: 12 },
  title: { fontFamily: fonts.display, fontSize: 20, color: c.onSurface },
  close: { width: 44, height: 44, alignItems: "center", justifyContent: "center", marginRight: -10 },
  footer: { paddingHorizontal: 16, paddingTop: 12, borderTopWidth: 1, borderTopColor: c.divider, backgroundColor: c.surface },
}));
