import { Ionicons } from "@react-native-vector-icons/ionicons";
import { Image } from "expo-image";
import { useRouter } from "expo-router";
import React from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAuth } from "@/src/auth";
import { Button } from "@/src/components/ui";
import { useLang } from "@/src/i18n";
import { usesNativeTabs } from "@/src/navigation";
import { fonts, makeStyles, useTheme } from "@/src/theme";

export default function Profile() {
  const insets = useSafeAreaInsets();
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;
  const styles = useStyles();
  const { colors } = useTheme();
  const { t, lang, setLang } = useLang();
  const { user, logout } = useAuth();
  const router = useRouter();

  return (
    <View style={styles.screen}>
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <Text style={styles.title}>{t("profile")}</Text>
      </View>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: bottomChrome + 24, gap: 16 }}>
        <View style={styles.card} testID="profile-card">
          {user ? (
            <View style={styles.userRow}>
              {user.picture ? (
                <Image source={{ uri: user.picture }} style={styles.avatar} />
              ) : (
                <View style={[styles.avatar, styles.avatarFallback]}>
                  <Text style={styles.avatarText}>{(user.name || user.email)[0]?.toUpperCase()}</Text>
                </View>
              )}
              <View style={{ flex: 1 }}>
                <Text style={styles.name} testID="profile-name">{user.name || user.email}</Text>
                <Text style={styles.email} testID="profile-email">{user.email}</Text>
                {user.role === "admin" && <Text style={styles.role}>ADMIN</Text>}
              </View>
            </View>
          ) : (
            <View style={{ gap: 12 }}>
              <Text style={styles.name}>{t("guest")}</Text>
              <Text style={styles.email}>{t("loginSub")}</Text>
              <Button label={t("signIn")} icon="logo-google" onPress={() => router.push("/login")} testID="profile-signin-btn" />
            </View>
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.rowLabel}>{t("language")}</Text>
          <View style={styles.segmented}>
            {([["en", "English"], ["hi", "हिंदी"]] as const).map(([k, label]) => (
              <Pressable key={k} testID={`lang-${k}-btn`} onPress={() => setLang(k)} style={[styles.segBtn, lang === k && styles.segBtnOn]}>
                <Text style={[styles.segText, lang === k && styles.segTextOn]}>{label}</Text>
              </Pressable>
            ))}
          </View>
        </View>

        {user?.role === "admin" && (
          <View style={styles.card}>
            <Text style={styles.rowLabel}>{t("adminTools")}</Text>
            <Pressable testID="admin-localities-link" onPress={() => router.push("/admin/localities")} style={styles.linkRow}>
              <Ionicons name="map-outline" size={22} color={colors.brandPrimary} />
              <Text style={styles.linkText}>{t("manageLocalities")}</Text>
              <Ionicons name="chevron-forward" size={20} color={colors.muted} />
            </Pressable>
          </View>
        )}

        <View style={styles.card}>
          <Text style={styles.rowLabel}>{t("aboutApp")}</Text>
          <Text style={styles.email}>{t("aboutText")}</Text>
        </View>

        {user && <Button label={t("logout")} variant="outline" icon="log-out-outline" onPress={logout} testID="logout-btn" />}
      </ScrollView>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  header: { backgroundColor: c.surface, paddingHorizontal: 16, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: c.divider },
  title: { fontFamily: fonts.display, fontSize: 28, color: c.onSurface },
  card: { backgroundColor: c.surface, borderRadius: 12, padding: 16, borderWidth: 1, borderColor: c.border, gap: 12 },
  userRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  avatar: { width: 56, height: 56, borderRadius: 28 },
  avatarFallback: { backgroundColor: c.brandTertiary, alignItems: "center", justifyContent: "center" },
  avatarText: { fontFamily: fonts.display, fontSize: 22, color: c.onBrandTertiary },
  name: { fontFamily: fonts.displaySemi, fontSize: 18, color: c.onSurface },
  email: { fontFamily: fonts.text, fontSize: 14, color: c.muted },
  role: { fontFamily: fonts.textSemi, fontSize: 11, color: c.brandPrimary, letterSpacing: 1, marginTop: 2 },
  rowLabel: { fontFamily: fonts.textSemi, fontSize: 14, color: c.onSurfaceSecondary },
  segmented: { flexDirection: "row", backgroundColor: c.surfaceTertiary, borderRadius: 12, padding: 4 },
  segBtn: { flex: 1, height: 40, borderRadius: 8, alignItems: "center", justifyContent: "center" },
  segBtnOn: { backgroundColor: c.surface },
  segText: { fontFamily: fonts.textMedium, fontSize: 15, color: c.onSurfaceTertiary },
  segTextOn: { color: c.brandPrimary, fontFamily: fonts.textSemi },
  linkRow: { flexDirection: "row", alignItems: "center", gap: 12, minHeight: 44 },
  linkText: { flex: 1, fontFamily: fonts.textMedium, fontSize: 15, color: c.onSurface },
}));
