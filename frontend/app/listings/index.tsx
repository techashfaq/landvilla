import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import { Redirect, useFocusEffect, useRouter } from "expo-router";
import React, { useCallback } from "react";
import { ActivityIndicator, Alert, FlatList, Pressable, RefreshControl, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useToast } from "@/src/components/Toast";
import { api, fileUrl } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Badge, Button, EmptyState, ScreenHeader } from "@/src/components/ui";
import { formatPrice } from "@/src/data";
import { useLang } from "@/src/i18n";
import { FEATURED_PURCHASE_ALLOWED, LISTING_STATUS } from "@/src/lister";
import { fonts, makeStyles, useTheme } from "@/src/theme";

export default function MyListings() {
  const qc = useQueryClient();
  const toast = useToast();
  const action = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) => api(`/listings/${id}/status`, { method: "POST", body: { action } }),
    onSuccess: () => { qc.invalidateQueries(); toast.show("Listing updated", "success"); },
    onError: (e: Error) => { toast.show(e.message, "error"); qc.invalidateQueries({ queryKey: ["my-listings"] }); },
  });
  const confirm = (id: string, kind: string) => Alert.alert(
    kind === "delete" ? "Remove listing?" : kind === "reactivate" ? "Submit for review?" : "Deactivate listing?",
    kind === "delete" ? "The listing will be removed. Existing enquiry and transaction records are retained." : kind === "reactivate" ? "An administrator must approve it before it becomes public again." : "This listing will no longer be visible to customers.",
    [{ text: "Cancel", style: "cancel" }, { text: "Confirm", style: kind === "delete" ? "destructive" : "default", onPress: () => { if (!action.isPending) action.mutate({ id, action: kind }); } }]);
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const { tx, pick, lang } = useLang();
  const router = useRouter();
  const { user, loading } = useAuth();
  const q = useInfiniteQuery({ queryKey: ["my-listings", user?.user_id], enabled: !!user,
    queryFn: ({ pageParam }) => api<{ items: any[]; total: number; page: number; limit: number }>(`/listings/mine?page=${pageParam}&limit=20`),
    initialPageParam: 1, getNextPageParam: last => last.page * last.limit < last.total ? last.page + 1 : undefined });
  const ownerId = user?.user_id;
  const refreshListings = q.refetch;
  useFocusEffect(useCallback(() => { if (ownerId) void refreshListings(); }, [ownerId, refreshListings]));
  const plans = useQuery({ queryKey: ["featured-plans"], queryFn: () => api<{ payments_configured: boolean }>("/featured-plans") });
  // Store policy: paid in-app promotion is not sold inside the Android/iOS apps until a compliant billing approach is approved.
  const canBuyFeatured = FEATURED_PURCHASE_ALLOWED && !!plans.data?.payments_configured;
  if (loading) return <ActivityIndicator />;
  if (!user) return <Redirect href="/login" />;

  return (
    <View style={styles.screen}>
      <ScreenHeader
        title={tx("My listings", "मेरी लिस्टिंग")}
        onBack={() => (router.canGoBack() ? router.back() : router.replace("/profile"))}
        topInset={insets.top}
        right={<Pressable testID="new-listing-btn" onPress={() => router.push("/post")} style={styles.add}><Ionicons name="add" size={22} color={colors.onBrandPrimary} /></Pressable>}
      />
      <Button label={tx("Open lead inbox", "लीड इनबॉक्स खोलें")} variant="outline" onPress={() => router.push("/leads")} style={{ margin: 16 }} />
      {q.isLoading ? (
        <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 40 }} />
      ) : q.isError ? <EmptyState icon="cloud-offline-outline" title={q.error.message} cta="Retry" onPress={() => q.refetch()} /> : (
        <FlatList
          data={q.data?.pages.flatMap(page => page.items) ?? []}
          onEndReached={() => { if (q.hasNextPage && !q.isFetching) q.fetchNextPage(); }}
          ListFooterComponent={q.isFetchingNextPage ? <ActivityIndicator /> : undefined}
          keyExtractor={(p) => p.id}
          contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: insets.bottom + 24 }}
          refreshControl={<RefreshControl refreshing={q.isRefetching} onRefresh={() => { q.refetch(); }} tintColor={colors.brandPrimary} />}
          ListEmptyComponent={<EmptyState icon="home-outline" title={tx("You haven't posted any property yet", "आपने अभी कोई प्रॉपर्टी पोस्ट नहीं की")} cta={tx("Post a property", "प्रॉपर्टी पोस्ट करें")} onPress={() => router.push("/post")} testID="my-listings-empty" />}
          renderItem={({ item: p }) => {
            const st = LISTING_STATUS[p.listing_status] ?? { en: "Status unavailable", hi: "स्थिति उपलब्ध नहीं", kind: "muted" as const };
            const featuredActive = p.featured && p.featured_until && new Date(p.featured_until) > new Date();
            return (
              <View style={styles.card} testID={`my-listing-${p.id}`}>
                <View style={{ flexDirection: "row", gap: 12 }}>
                  <Image source={{ uri: fileUrl(p.images?.[0]) }} style={styles.thumb} contentFit="cover" />
                  <View style={{ flex: 1, gap: 4 }}>
                    <Text style={styles.title} numberOfLines={1}>{pick(p, "title")}</Text>
                    <Text style={styles.sub}>{formatPrice(p.price, p.purpose, lang)} · {pick(p.locality, "name")}</Text>
                    <View style={{ flexDirection: "row", gap: 6, flexWrap: "wrap" }}>
                      <Badge label={tx(st.en, st.hi)} kind={st.kind} testID={`listing-status-${p.id}`} />
                      {featuredActive && <Badge label={tx("Featured", "फ़ीचर्ड")} kind="featured" />}
                      <Badge label={`${p.lead_count} ${tx("leads", "लीड")}`} kind="muted" />
                    </View>
                  </View>
                </View>
                {featuredActive && (
                  <Text style={styles.small}>{tx("Featured until", "फ़ीचर्ड तक")} {new Date(p.featured_until).toLocaleDateString(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short", year: "numeric" })}</Text>
                )}
                {p.moderation?.note && p.listing_status !== "active" ? <Text style={styles.note}>{tx("Reviewer note", "समीक्षक नोट")}: {p.moderation.note}</Text> : null}
                <View style={styles.actions}>
                  {!["sold_rented", "expired", "deleted"].includes(p.listing_status) && (
                    <Button label={tx("Edit", "बदलें")} variant="outline" icon="create-outline" onPress={() => router.push(`/post/form?id=${p.id}`)} testID={`edit-listing-${p.id}`} style={{ flex: 1 }} />
                  )}
                  {p.listing_status === "active" && (
                    <Button label={canBuyFeatured ? featuredActive ? tx("Extend", "बढ़ाएं") : tx("Feature", "फ़ीचर करें") : tx("Packages", "पैकेज")} icon="star-outline" onPress={() => router.push(`/feature/${p.id}`)} testID={`feature-listing-${p.id}`} style={{ flex: 1 }} />
                  )}
                  {[...( ["active", "pending_review", "changes_requested"].includes(p.listing_status) ? ["deactivate"] : []), ...(p.listing_status === "inactive" ? ["reactivate"] : []), ...(["active", "pending_review", "changes_requested", "rejected", "inactive", "expired", "sold_rented"].includes(p.listing_status) ? ["delete"] : [])].map(kind => <Button key={kind} label={kind === "delete" ? "Remove" : kind === "reactivate" ? "Reactivate" : "Deactivate"} variant="outline" disabled={action.isPending} loading={action.isPending && action.variables?.id === p.id && action.variables?.action === kind} onPress={() => confirm(p.id, kind)} />)}
                </View>
              </View>
            );
          }}
        />
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  add: { width: 40, height: 40, borderRadius: 20, backgroundColor: c.brandPrimary, alignItems: "center", justifyContent: "center", marginRight: 8 },
  card: { backgroundColor: c.surface, borderRadius: 12, padding: 12, borderWidth: 1, borderColor: c.border, gap: 10 },
  thumb: { width: 84, height: 84, borderRadius: 8, backgroundColor: c.surfaceTertiary },
  title: { fontFamily: fonts.textSemi, fontSize: 15, color: c.onSurface },
  sub: { fontFamily: fonts.textMedium, fontSize: 13, color: c.brandPrimary },
  small: { fontFamily: fonts.text, fontSize: 12, color: c.muted },
  note: { fontFamily: fonts.textMedium, fontSize: 13, color: c.error },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
}));
