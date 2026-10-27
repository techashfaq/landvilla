import { Ionicons } from "@react-native-vector-icons/ionicons";
import React from "react";
import { ActivityIndicator, Pressable, Text, View, ViewStyle } from "react-native";
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from "react-native-reanimated";

import { fonts, makeStyles, useTheme } from "@/src/theme";

export function Chip({ label, selected, onPress, testID, icon }: { label: string; selected?: boolean; onPress: () => void; testID?: string; icon?: any }) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      testID={testID}
      hitSlop={{ top: 4, bottom: 4 }}
      style={({ pressed }) => [styles.chip, selected && styles.chipOn, pressed && { opacity: 0.75 }]}
    >
      {icon && <Ionicons name={icon} size={16} color={selected ? colors.onBrandTertiary : colors.onSurfaceTertiary} />}
      <Text style={[styles.chipText, selected && styles.chipTextOn]} numberOfLines={1}>
        {label}
      </Text>
    </Pressable>
  );
}

export function Button({
  label,
  onPress,
  loading,
  disabled,
  variant = "primary",
  testID,
  icon,
  style,
}: {
  label: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  variant?: "primary" | "outline";
  testID?: string;
  icon?: any;
  style?: ViewStyle;
}) {
  const styles = useStyles();
  const { colors } = useTheme();
  const scale = useSharedValue(1);
  const anim = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  const fg = variant === "primary" ? colors.onBrandPrimary : colors.brandPrimary;
  return (
    <Animated.View style={[anim, style]}>
      <Pressable
        testID={testID}
        disabled={disabled || loading}
        onPress={onPress}
        onPressIn={() => (scale.value = withSpring(0.97))}
        onPressOut={() => (scale.value = withSpring(1))}
        style={[styles.btn, variant === "outline" && styles.btnOutline, (disabled || loading) && { opacity: 0.6 }]}
      >
        {loading ? (
          <ActivityIndicator color={fg} />
        ) : (
          <>
            {icon && <Ionicons name={icon} size={18} color={fg} />}
            <Text style={[styles.btnText, { color: fg }]}>{label}</Text>
          </>
        )}
      </Pressable>
    </Animated.View>
  );
}

export function EmptyState({ icon, title, cta, onPress, testID }: { icon: any; title: string; cta?: string; onPress?: () => void; testID?: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <View style={styles.empty} testID={testID}>
      <View style={styles.emptyIcon}>
        <Ionicons name={icon} size={36} color={colors.brandPrimary} />
      </View>
      <Text style={styles.emptyTitle}>{title}</Text>
      {cta && onPress && <Button label={cta} onPress={onPress} testID={`${testID}-cta`} style={{ marginTop: 16 }} />}
    </View>
  );
}

export function Badge({ label, kind, testID }: { label: string; kind: "verified" | "demo" | "featured" | "muted"; testID?: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const map = {
    verified: { bg: colors.success, fg: colors.onSuccess, icon: "shield-checkmark" },
    demo: { bg: colors.warning, fg: colors.onWarning, icon: "flask" },
    featured: { bg: colors.brandPrimary, fg: colors.onBrandPrimary, icon: "star" },
    muted: { bg: colors.surfaceTertiary, fg: colors.onSurfaceTertiary, icon: "time-outline" },
  }[kind];
  return (
    <View style={[styles.badge, { backgroundColor: map.bg }]} testID={testID}>
      <Ionicons name={map.icon as any} size={11} color={map.fg} />
      <Text style={[styles.badgeText, { color: map.fg }]}>{label}</Text>
    </View>
  );
}

export function Checkbox({ checked, onToggle, label, testID }: { checked: boolean; onToggle: () => void; label: string; testID?: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <Pressable onPress={onToggle} testID={testID} style={styles.checkRow} accessibilityRole="checkbox" accessibilityState={{ checked }}>
      <View style={[styles.checkBox, checked && { backgroundColor: colors.brandPrimary, borderColor: colors.brandPrimary }]}>
        {checked && <Ionicons name="checkmark" size={16} color={colors.onBrandPrimary} />}
      </View>
      <Text style={styles.checkLabel}>{label}</Text>
    </Pressable>
  );
}

export function ScreenHeader({ title, onBack, right, topInset }: { title: string; onBack: () => void; right?: React.ReactNode; topInset: number }) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <View style={[styles.sHeader, { paddingTop: topInset + 8 }]}>
      <Pressable testID="screen-back-btn" onPress={onBack} style={styles.sBack} hitSlop={8}>
        <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
      </Pressable>
      <Text style={styles.sTitle} numberOfLines={1}>{title}</Text>
      <View style={{ minWidth: 44, alignItems: "flex-end" }}>{right}</View>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  checkRow: { flexDirection: "row", gap: 12, alignItems: "flex-start", paddingVertical: 12 },
  checkBox: { width: 24, height: 24, borderRadius: 6, borderWidth: 2, borderColor: c.borderStrong, alignItems: "center", justifyContent: "center", marginTop: 1 },
  checkLabel: { flex: 1, fontFamily: fonts.textMedium, fontSize: 14, color: c.onSurface, lineHeight: 20 },
  sHeader: { flexDirection: "row", alignItems: "center", paddingHorizontal: 8, paddingBottom: 8, backgroundColor: c.surface, borderBottomWidth: 1, borderBottomColor: c.divider },
  sBack: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  sTitle: { flex: 1, fontFamily: fonts.display, fontSize: 20, color: c.onSurface, marginLeft: 4 },
  chip: {
    height: 36,
    flexShrink: 0,
    paddingHorizontal: 14,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surface,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  chipOn: { backgroundColor: c.brandTertiary, borderColor: c.brandPrimary },
  chipText: { fontFamily: fonts.textMedium, fontSize: 14, color: c.onSurfaceTertiary },
  chipTextOn: { color: c.onBrandTertiary },
  btn: {
    height: 52,
    borderRadius: 12,
    backgroundColor: c.brandPrimary,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 20,
  },
  btnOutline: { backgroundColor: c.surface, borderWidth: 1.5, borderColor: c.brandPrimary },
  btnText: { fontFamily: fonts.textSemi, fontSize: 16 },
  empty: { alignItems: "center", paddingVertical: 48, paddingHorizontal: 24 },
  emptyIcon: { width: 80, height: 80, borderRadius: 40, backgroundColor: c.brandTertiary, alignItems: "center", justifyContent: "center", marginBottom: 16 },
  emptyTitle: { fontFamily: fonts.displaySemi, fontSize: 18, color: c.onSurface, textAlign: "center" },
  badge: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 8, height: 22, borderRadius: 6 },
  badgeText: { fontFamily: fonts.textSemi, fontSize: 11, letterSpacing: 0.4 },
}));
