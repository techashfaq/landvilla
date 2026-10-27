import { useQuery } from "@tanstack/react-query";
import { Image } from "expo-image";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { ActivityIndicator, FlatList, Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, fileUrl } from "@/src/api";
import { Badge, Chip, EmptyState, ScreenHeader } from "@/src/components/ui";
import { useLang } from "@/src/i18n";
import { LEAD_STATUS } from "@/src/lister";
import { fonts, makeStyles, useTheme } from "@/src/theme";

export default function LeadInbox() {
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const { tx, pick, lang } = useLang();
  const router = useRouter();
  const [status, setStatus] = useState<string | undefined>();
  const q = useQuery({ queryKey: ["leads", status], queryFn: () => api<{ items: any[]; counts: Record<string, number> }>(`/leads${status ? `?status=${status}` : ""}`) });
  const counts = q.data?.counts ?? {};
  const total = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <View style={styles.screen}>
      <View style={styles.headWrap}>
        <ScreenHeader title={tx("Lead inbox", "लीड इनबॉक्स")} onBack={() => (router.canGoBack() ? router.back() : router.replace("/profile"))} topInset={insets.top} />
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ height: 56, flexGrow: 0 }} contentContainerStyle={{ gap: 8, paddingHorizontal: 16, alignItems: "center" }}>
          <Chip label={`${tx("All", "सभी")} ${total}`} selected={!status} onPress={() => setStatus(undefined)} testID="lead-filter-all" />
          {Object.entries(LEAD_STATUS).map(([k, v]) => (
            <Chip key={k} label={`${tx(v.en, v.hi)} ${counts[k] ?? 0}`} selected={status === k} onPress={() => setStatus(k)} testID={`lead-filter-${k}`} />
          ))}
        </ScrollView>
      </View>
      {q.isLoading ? (
        <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={q.data?.items ?? []}
          keyExtractor={(l) => l.id}
          contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: insets.bottom + 24 }}
          refreshControl={<RefreshControl refreshing={q.isRefetching} onRefresh={() => { q.refetch(); }} tintColor={colors.brandPrimary} />}
          ListEmptyComponent={<EmptyState icon="mail-open-outline" title={tx("No enquiries yet. Leads on your listings will appear here.", "अभी कोई पूछताछ नहीं। आपकी लिस्टिंग की लीड यहाँ दिखेंगी।")} testID="leads-empty" />}
          renderItem={({ item: l }) => (
            <Pressable testID={`lead-item-${l.id}`} style={styles.card} onPress={() => router.push(`/leads/${l.id}`)}>
              {l.property?.images?.[0] ? <Image source={{ uri: fileUrl(l.property.images[0]) }} style={styles.thumb} contentFit="cover" /> : <View style={styles.thumb} />}
              <View style={{ flex: 1, gap: 3 }}>
                <Text style={styles.name}>{l.name}</Text>
                <Text style={styles.sub} numberOfLines={1}>{l.property ? pick(l.property, "title") : "—"}</Text>
                <Text style={styles.phone}>{l.share_phone_consent ? tx("Number shared – open to view", "नंबर साझा – देखने के लिए खोलें") : `${l.phone_masked} · ${tx("in-app only", "केवल ऐप में")}`}</Text>
                <View style={{ flexDirection: "row", gap: 6, flexWrap: "wrap" }}>
                  <Badge label={tx(LEAD_STATUS[l.status]?.en ?? l.status, LEAD_STATUS[l.status]?.hi ?? l.status)} kind={l.status === "new" ? "featured" : l.status === "closed" ? "muted" : "verified"} testID={`lead-status-${l.id}`} />
                  {l.follow_up_at && <Badge label={`${tx("Follow-up", "फ़ॉलो-अप")} ${new Date(l.follow_up_at).toLocaleDateString(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short" })}`} kind="muted" />}
                  {l.message_count > 0 && <Badge label={`${l.message_count} msg`} kind="muted" />}
                </View>
              </View>
            </Pressable>
          )}
        />
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  headWrap: { backgroundColor: c.surface, borderBottomWidth: 1, borderBottomColor: c.divider },
  card: { flexDirection: "row", gap: 12, padding: 12, borderRadius: 12, backgroundColor: c.surface, borderWidth: 1, borderColor: c.border },
  thumb: { width: 72, height: 72, borderRadius: 8, backgroundColor: c.surfaceTertiary },
  name: { fontFamily: fonts.textSemi, fontSize: 15, color: c.onSurface },
  sub: { fontFamily: fonts.text, fontSize: 13, color: c.onSurfaceTertiary },
  phone: { fontFamily: fonts.textMedium, fontSize: 12, color: c.muted },
}));
