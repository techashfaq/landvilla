import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useQuery } from "@tanstack/react-query";
import { Image } from "expo-image";
import { useRouter } from "expo-router";
import React from "react";
import { ActivityIndicator, FlatList, Pressable, RefreshControl, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Badge, EmptyState } from "@/src/components/ui";
import { formatPrice, Property } from "@/src/data";
import { useLang } from "@/src/i18n";
import { usesNativeTabs } from "@/src/navigation";
import { fonts, makeStyles, useTheme } from "@/src/theme";

type Enquiry = { id: string; property_id: string; intent: string; status: string; message: string; created_at: string; property?: Property };

export default function Enquiries() {
  const insets = useSafeAreaInsets();
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;
  const styles = useStyles();
  const { colors } = useTheme();
  const { t, pick, lang } = useLang();
  const { user } = useAuth();
  const router = useRouter();
  const q = useQuery({ queryKey: ["enquiries", user?.user_id], queryFn: () => api<{ items: Enquiry[] }>("/enquiries/me"), enabled: !!user });

  const statusLabel = (s: string) => (s === "contacted" ? t("statusContacted") : s === "closed" ? t("statusClosed") : t("statusNew"));
  const intentLabel = (s: string) => (s === "site_visit" ? t("intentVisit") : s === "callback" ? t("intentCallback") : t("intentInfo"));

  return (
    <View style={styles.screen}>
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <Text style={styles.title} testID="enquiries-title">{t("enquiries")}</Text>
      </View>
      {!user ? (
        <EmptyState icon="chatbubbles-outline" title={t("loginRequired")} cta={t("signIn")} onPress={() => router.push("/login")} testID="enquiries-login" />
      ) : q.isLoading ? (
        <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 48 }} />
      ) : q.isError ? (
        <EmptyState icon="cloud-offline-outline" title={t("loadError")} cta={t("retry")} onPress={() => q.refetch()} testID="enquiries-error" />
      ) : (
        <FlatList
          data={q.data?.items ?? []}
          keyExtractor={(e) => e.id}
          contentContainerStyle={{ padding: 16, paddingBottom: bottomChrome + 24, gap: 12 }}
          refreshControl={<RefreshControl refreshing={q.isRefetching} onRefresh={() => { q.refetch(); }} tintColor={colors.brandPrimary} />}
          renderItem={({ item }) => (
            <Pressable
              testID={`enquiry-item-${item.id}`}
              style={styles.card}
              onPress={() => item.property && router.push(`/property/${item.property_id}`)}
            >
              {item.property?.images?.[0] ? (
                <Image source={{ uri: item.property.images[0] }} style={styles.thumb} contentFit="cover" />
              ) : (
                <View style={[styles.thumb, { alignItems: "center", justifyContent: "center" }]}>
                  <Ionicons name="home-outline" size={24} color={colors.muted} />
                </View>
              )}
              <View style={{ flex: 1, gap: 4 }}>
                <Text style={styles.cardTitle} numberOfLines={1}>{item.property ? pick(item.property, "title") : "—"}</Text>
                {item.property && (
                  <Text style={styles.cardSub} numberOfLines={1}>
                    {formatPrice(item.property.price, item.property.purpose, lang)} · {pick(item.property.locality, "name")}
                  </Text>
                )}
                <Text style={styles.cardMeta}>
                  {intentLabel(item.intent)} · {t("sentOn")} {new Date(item.created_at).toLocaleDateString(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short" })}
                </Text>
                <View style={{ flexDirection: "row", gap: 6, marginTop: 2 }}>
                  <Badge label={statusLabel(item.status)} kind={item.status === "contacted" ? "verified" : "muted"} testID={`enquiry-status-${item.id}`} />
                  {item.property?.is_demo && <Badge label={t("demo")} kind="demo" />}
                </View>
              </View>
            </Pressable>
          )}
          ListEmptyComponent={<EmptyState icon="chatbubbles-outline" title={t("enquiriesEmpty")} cta={t("browseHomes")} onPress={() => router.navigate("/")} testID="enquiries-empty" />}
        />
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  header: { backgroundColor: c.surface, paddingHorizontal: 16, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: c.divider },
  title: { fontFamily: fonts.display, fontSize: 28, color: c.onSurface },
  card: { flexDirection: "row", gap: 12, padding: 12, borderRadius: 12, backgroundColor: c.surface, borderWidth: 1, borderColor: c.border },
  thumb: { width: 84, height: 84, borderRadius: 8, backgroundColor: c.surfaceTertiary },
  cardTitle: { fontFamily: fonts.textSemi, fontSize: 15, color: c.onSurface },
  cardSub: { fontFamily: fonts.textMedium, fontSize: 13, color: c.brandPrimary },
  cardMeta: { fontFamily: fonts.text, fontSize: 12, color: c.muted },
}));
