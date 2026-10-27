import { Ionicons } from "@react-native-vector-icons/ionicons";
import { Image } from "expo-image";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Sheet } from "@/src/components/Sheet";
import { useToast } from "@/src/components/Toast";
import { Button } from "@/src/components/ui";
import { useLang } from "@/src/i18n";
import { usesNativeTabs } from "@/src/navigation";
import { fonts, makeStyles, useTheme } from "@/src/theme";

export default function Profile() {
  const insets = useSafeAreaInsets();
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;
  const styles = useStyles();
  const { colors } = useTheme();
  const { t, lang, setLang, tx } = useLang();
  const { user, logout } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [delOpen, setDelOpen] = useState(false);
  const [confirm, setConfirm] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [delErr, setDelErr] = useState("");
  const doDelete = async () => {
    setDeleting(true);
    setDelErr("");
    try {
      await api("/account/delete", { method: "POST", body: { confirm } });
      setDelOpen(false);
      await logout();
      toast.show(tx("Your account has been deleted", "आपका खाता हटा दिया गया है"), "success");
    } catch (e: any) {
      if (e.status === 403 && String(e.message).startsWith("reauth_required")) {
        setDelOpen(false);
        toast.show(tx("For your security, please sign in again, then delete your account.", "सुरक्षा के लिए दोबारा साइन इन करें, फिर खाता हटाएं।"), "info");
        await logout();
        router.push("/login");
        return;
      }
      setDelErr(e.message);
    } finally {
      setDeleting(false);
    }
  };

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

        {user && (
          <View style={styles.card}>
            <Text style={styles.rowLabel}>{tx("Sell or rent out", "बेचें या किराए पर दें")}</Text>
            {([
              ["add-circle-outline", tx("Post a property", "प्रॉपर्टी पोस्ट करें"), "/post", "profile-post-link"],
              ["list-outline", tx("My listings", "मेरी लिस्टिंग"), "/listings", "profile-my-listings-link"],
              ["mail-unread-outline", tx("Lead inbox", "लीड इनबॉक्स"), "/leads", "profile-leads-link"],
            ] as const).map(([icon, label, href, tid]) => (
              <Pressable key={href} testID={tid} onPress={() => router.push(href as any)} style={styles.linkRow}>
                <Ionicons name={icon} size={22} color={colors.brandPrimary} />
                <Text style={styles.linkText}>{label}</Text>
                <Ionicons name="chevron-forward" size={20} color={colors.muted} />
              </Pressable>
            ))}
          </View>
        )}

        {user?.role === "admin" && (
          <View style={styles.card}>
            <Text style={styles.rowLabel}>{t("adminTools")}</Text>
            {([
              ["checkmark-done-outline", "Approval queue", "/admin/listings", "admin-listings-link"],
              ["briefcase-outline", "Broker verification", "/admin/brokers", "admin-brokers-link"],
              ["star-outline", "Featured plans & payments", "/admin/plans", "admin-plans-link"],
              ["flag-outline", "Reports & deletion requests", "/admin/reports", "admin-reports-link"],
              ["document-lock-outline", "Commission agreements", "/admin/commissions", "admin-commissions-link"],
            ] as const).map(([icon, label, href, tid]) => (
              <Pressable key={href} testID={tid} onPress={() => router.push(href as any)} style={styles.linkRow}>
                <Ionicons name={icon} size={22} color={colors.brandPrimary} />
                <Text style={styles.linkText}>{label}</Text>
                <Ionicons name="chevron-forward" size={20} color={colors.muted} />
              </Pressable>
            ))}
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
          {([["document-text-outline", tx("Privacy Policy", "गोपनीयता नीति"), "/legal/privacy", "privacy-link"],
            ["reader-outline", tx("Terms & Conditions", "नियम और शर्तें"), "/legal/terms", "terms-link"]] as const).map(([icon, label, href, tid]) => (
            <Pressable key={href} testID={tid} onPress={() => router.push(href as any)} style={styles.linkRow}>
              <Ionicons name={icon} size={22} color={colors.brandPrimary} />
              <Text style={styles.linkText}>{label}</Text>
              <Ionicons name="chevron-forward" size={20} color={colors.muted} />
            </Pressable>
          ))}
        </View>

        {user && <Button label={t("logout")} variant="outline" icon="log-out-outline" onPress={logout} testID="logout-btn" />}
        {user && (
          <Pressable testID="delete-account-btn" onPress={() => { setConfirm(""); setDelErr(""); setDelOpen(true); }} style={styles.deleteRow}>
            <Ionicons name="trash-outline" size={20} color={colors.error} />
            <Text style={styles.deleteText}>{tx("Delete account", "खाता हटाएं")}</Text>
          </Pressable>
        )}
      </ScrollView>
      <Sheet visible={delOpen} onClose={() => setDelOpen(false)} title={tx("Delete account", "खाता हटाएं")} testID="delete-account-sheet"
        footer={<Button label={tx("Permanently delete", "स्थायी रूप से हटाएं")} disabled={confirm.trim().toUpperCase() !== "DELETE"} loading={deleting} onPress={doDelete} testID="delete-account-confirm-btn" />}>
        <View style={{ paddingHorizontal: 16, paddingBottom: 16, gap: 12 }}>
          <Text style={styles.email}>{tx(
            "This deletes your account, saved homes, broker profile and documents, removes your listings, and anonymises your enquiries and messages. Payment records are kept only as required by tax law. This cannot be undone.",
            "इससे आपका खाता, सेव किए घर, ब्रोकर प्रोफ़ाइल और दस्तावेज़ हट जाएंगे, आपकी लिस्टिंग हटा दी जाएंगी, और पूछताछ व संदेश गुमनाम कर दिए जाएंगे। भुगतान रिकॉर्ड केवल कर कानून के अनुसार रखे जाते हैं। इसे वापस नहीं किया जा सकता।")}</Text>
          <Text style={styles.rowLabel}>{tx("Type DELETE to confirm", "पुष्टि के लिए DELETE लिखें")}</Text>
          <TextInput testID="delete-account-input" value={confirm} onChangeText={setConfirm} autoCapitalize="characters" style={styles.input} placeholder="DELETE" placeholderTextColor={colors.muted} />
          {!!delErr && <Text style={{ color: colors.error }} testID="delete-account-error">{delErr}</Text>}
        </View>
      </Sheet>
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
  deleteRow: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, minHeight: 48 },
  deleteText: { fontFamily: fonts.textSemi, fontSize: 15, color: c.error },
  input: { height: 48, borderRadius: 12, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, paddingHorizontal: 12, fontFamily: fonts.text, fontSize: 16, color: c.onSurface },
}));
