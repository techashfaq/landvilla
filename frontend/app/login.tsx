import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useRouter } from "expo-router";
import React, { useEffect } from "react";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAuth } from "@/src/auth";
import { Button } from "@/src/components/ui";
import { useLang } from "@/src/i18n";
import { fonts, makeStyles, useTheme } from "@/src/theme";

export default function Login() {
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const { t, tx } = useLang();
  const { user, login, signingIn, error } = useAuth();
  const router = useRouter();

  // Auth gate: once signed in, leave the login screen.
  useEffect(() => {
    if (user) {
      if (router.canGoBack()) router.back();
      else router.replace("/");
    }
  }, [user, router]);

  return (
    <View style={[styles.screen, { paddingTop: insets.top + 8, paddingBottom: insets.bottom + 24 }]}>
      <Pressable testID="login-close-btn" onPress={() => (router.canGoBack() ? router.back() : router.replace("/"))} style={styles.close}>
        <Ionicons name="close" size={26} color={colors.onSurface} />
      </Pressable>
      <View style={styles.body}>
        <View style={styles.logo}>
          <Ionicons name="home" size={40} color={colors.onBrandPrimary} />
        </View>
        <Text style={styles.brand}>LANDVILLA</Text>
        <Text style={styles.title}>{t("loginTitle")}</Text>
        <Text style={styles.sub}>{t("loginSub")}</Text>
      </View>
      {error && <Text style={styles.err} testID="login-error">{error}</Text>}
      <Button label={t("continueGoogle")} icon="logo-google" onPress={login} loading={signingIn} testID="google-login-btn" />
      <Text style={styles.legal}>
        {tx("By continuing you agree to the ", "जारी रखकर आप ")}
        <Text style={styles.link} onPress={() => router.push("/legal/terms")} testID="login-terms-link">{tx("Terms", "नियम")}</Text>
        {tx(" and ", " और ")}
        <Text style={styles.link} onPress={() => router.push("/legal/privacy")} testID="login-privacy-link">{tx("Privacy Policy", "गोपनीयता नीति")}</Text>
        {tx(".", " से सहमत हैं।")}
      </Text>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surface, paddingHorizontal: 24 },
  close: { width: 44, height: 44, alignItems: "center", justifyContent: "center", marginLeft: -10 },
  body: { flex: 1, justifyContent: "center", alignItems: "flex-start", gap: 8 },
  logo: { width: 72, height: 72, borderRadius: 20, backgroundColor: c.brandPrimary, alignItems: "center", justifyContent: "center", marginBottom: 16 },
  brand: { fontFamily: fonts.display, fontSize: 16, color: c.brandPrimary, letterSpacing: 2 },
  title: { fontFamily: fonts.display, fontSize: 30, color: c.onSurface, lineHeight: 38 },
  sub: { fontFamily: fonts.text, fontSize: 16, color: c.muted, lineHeight: 24 },
  err: { color: c.error, fontFamily: fonts.textMedium, marginBottom: 12 },
  legal: { fontFamily: fonts.text, fontSize: 12, color: c.muted, textAlign: "center", marginTop: 12, lineHeight: 18 },
  link: { color: c.brandPrimary, fontFamily: fonts.textSemi },
}));
