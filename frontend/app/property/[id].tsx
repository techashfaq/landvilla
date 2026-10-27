import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useQuery } from "@tanstack/react-query";
import { BlurView } from "expo-blur";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Share, Text, useWindowDimensions, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, fileUrl } from "@/src/api";
import { useAuth } from "@/src/auth";
import { EnquirySheet } from "@/src/components/EnquirySheet";
import { Badge, Button, EmptyState } from "@/src/components/ui";
import { formatPrice, Property, useMeta, useToggleSave } from "@/src/data";
import { useLang } from "@/src/i18n";
import { fonts, makeStyles, useTheme } from "@/src/theme";

export default function PropertyDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const styles = useStyles();
  const { colors } = useTheme();
  const { t, pick, lang, tx } = useLang();
  const { user } = useAuth();
  const router = useRouter();
  const { data: meta } = useMeta();
  const toggleSave = useToggleSave();
  const [imgIdx, setImgIdx] = useState(0);
  const [enquiry, setEnquiry] = useState(false);
  const q = useQuery({ queryKey: ["property", id, user?.user_id], queryFn: () => api<Property>(`/properties/${id}`) });
  const p = q.data;
  const goBack = () => (router.canGoBack() ? router.back() : router.replace("/"));

  if (q.isLoading) {
    return (
      <View style={[styles.screen, styles.center]}>
        <ActivityIndicator color={colors.brandPrimary} size="large" />
      </View>
    );
  }
  if (q.isError || !p) {
    const notFound = (q.error as any)?.status === 404;
    return (
      <View style={[styles.screen, styles.center, { paddingTop: insets.top }]}>
        <EmptyState
          icon={notFound ? "home-outline" : "cloud-offline-outline"}
          title={notFound ? t("notAvailable") : t("loadError")}
          cta={notFound ? t("backHome") : t("retry")}
          onPress={notFound ? goBack : () => q.refetch()}
          testID="property-error"
        />
      </View>
    );
  }

  const amenities = (meta?.amenities ?? []).filter((a) => p.amenities.includes(a.slug));
  const ptype = meta?.property_types.find((x) => x.slug === p.type);
  const openEnquiry = () => (user ? setEnquiry(true) : router.push("/login"));

  return (
    <View style={styles.screen}>
      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom + 110 }} testID="property-detail-scroll">
        <View style={{ height: 320 }}>
          <ScrollView
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            onMomentumScrollEnd={(e) => setImgIdx(Math.round(e.nativeEvent.contentOffset.x / width))}
          >
            {p.images.map((src, i) => (
              <Image key={i} source={{ uri: fileUrl(src) }} style={{ width, height: 320 }} contentFit="cover" transition={200} />
            ))}
          </ScrollView>
          <LinearGradient colors={["rgba(0,0,0,0.5)", "transparent"]} style={styles.topScrim} pointerEvents="none" />
          {p.images.length > 1 && (
            <View style={styles.pager}>
              <Text style={styles.pagerText}>{imgIdx + 1}/{p.images.length}</Text>
            </View>
          )}
        </View>

        <View style={styles.content}>
          {p.is_demo && (
            <View style={styles.demoBanner} testID="demo-banner">
              <Ionicons name="flask-outline" size={18} color={colors.warning} />
              <Text style={styles.demoText}>{t("demoBanner")}</Text>
            </View>
          )}
          <View style={styles.badgeRow}>
            {p.is_demo && <Badge label={t("demo")} kind="demo" />}
            <Badge label={p.verification_status === "verified" ? t("verified") : t("unverified")} kind={p.verification_status === "verified" ? "verified" : "muted"} testID="verification-badge" />
            {ptype && <Badge label={pick(ptype, "name")} kind="muted" />}
          </View>
          <Text style={styles.price} testID="detail-price">{formatPrice(p.price, p.purpose, lang)}</Text>
          <Text style={styles.title} testID="detail-title">{pick(p, "title")}</Text>
          <View style={styles.locRow}>
            <Ionicons name="location" size={16} color={colors.brandPrimary} />
            <Text style={styles.loc} testID="detail-locality">
              {pick(p.locality, "name")}{p.zone ? `, ${pick(p.zone, "name")}` : ""}, {lang === "hi" ? "उज्जैन" : "Ujjain"}
            </Text>
          </View>

          <View style={styles.stats}>
            {p.bhk ? <Stat icon="bed-outline" value={`${p.bhk}`} label={t("bhk")} /> : null}
            {p.bathrooms ? <Stat icon="water-outline" value={`${p.bathrooms}`} label={t("baths")} /> : null}
            {p.area_sqft ? <Stat icon="resize-outline" value={p.area_sqft.toLocaleString("en-IN")} label={t("sqft")} /> : null}
            {p.furnishing ? <Stat icon="cube-outline" value={t(p.furnishing as any)} label={t("furnishing")} /> : null}
          </View>

          {amenities.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>{t("amenities")}</Text>
              <View style={styles.amenGrid}>
                {amenities.map((a) => (
                  <View key={a.slug} style={styles.amen} testID={`amenity-${a.slug}`}>
                    <View style={styles.amenIcon}>
                      <Ionicons name={(a.icon as any) || "checkmark"} size={22} color={colors.brandPrimary} />
                    </View>
                    <Text style={styles.amenText} numberOfLines={2}>{pick(a, "name")}</Text>
                  </View>
                ))}
              </View>
            </View>
          )}

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{t("location")}</Text>
            <View style={styles.locCard}>
              <Ionicons name="map-outline" size={28} color={colors.brandPrimary} />
              <View style={{ flex: 1 }}>
                <Text style={styles.locCardTitle}>{pick(p.locality, "name")}</Text>
                {p.locality?.verification_status !== "verified" && <Text style={styles.locNote}>{t("notVerifiedNote")}</Text>}
              </View>
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{t("about")}</Text>
            <Text style={styles.desc}>{pick(p, "description")}</Text>
            <Text style={styles.disclaimer} testID="moderation-disclaimer">{tx("Listing moderation by LANDVILLA is not a guarantee of title, ownership, approvals or legal status. Please do your own legal due diligence.", "LANDVILLA द्वारा लिस्टिंग की जाँच, मालिकाना हक़, स्वामित्व, अनुमतियों या कानूनी स्थिति की गारंटी नहीं है। कृपया स्वयं कानूनी जाँच करें।")}</Text>
          </View>
        </View>
      </ScrollView>

      {/* Glass header */}
      <View style={[styles.headerBar, { top: insets.top + 8 }]}>
        <GlassBtn testID="detail-back-btn" icon="chevron-back" onPress={goBack} />
        <View style={{ flexDirection: "row", gap: 8 }}>
          <GlassBtn testID="detail-share-btn" icon="share-outline" onPress={() => Share.share({ message: `${pick(p, "title")} – ${formatPrice(p.price, p.purpose, lang)} · LANDVILLA` })} />
          <GlassBtn testID="detail-save-btn" icon={p.is_saved ? "heart" : "heart-outline"} active={p.is_saved} onPress={() => toggleSave(p.id, p.is_saved)} />
        </View>
      </View>

      {/* Sticky CTA */}
      <BlurView intensity={60} tint="light" style={[styles.cta, { paddingBottom: insets.bottom + 12 }]}>
        <View style={{ flex: 1 }}>
          <Text style={styles.ctaPrice}>{formatPrice(p.price, p.purpose, lang)}</Text>
          <Text style={styles.ctaSub} numberOfLines={1}>{pick(p.locality, "name")}</Text>
        </View>
        <Button label={t("enquireNow")} icon="chatbubble-ellipses-outline" onPress={openEnquiry} testID="enquire-now-btn" style={{ flex: 1.3 }} />
      </BlurView>

      <EnquirySheet visible={enquiry} onClose={() => setEnquiry(false)} propertyId={p.id} />
    </View>
  );
}

function GlassBtn({ icon, onPress, testID, active }: { icon: any; onPress: () => void; testID: string; active?: boolean }) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <Pressable onPress={onPress} testID={testID} style={styles.glassBtn}>
      <Ionicons name={icon} size={22} color={active ? colors.brandPrimary : colors.onSurface} />
    </Pressable>
  );
}

function Stat({ icon, value, label }: { icon: any; value: string; label: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <View style={styles.stat}>
      <Ionicons name={icon} size={20} color={colors.brandPrimary} />
      <Text style={styles.statVal} numberOfLines={2}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surface },
  center: { alignItems: "center", justifyContent: "center" },
  topScrim: { position: "absolute", top: 0, left: 0, right: 0, height: 120 },
  pager: { position: "absolute", bottom: 32, right: 16, backgroundColor: "rgba(28,25,23,0.6)", paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  pagerText: { color: "#FFFFFF", fontFamily: fonts.textSemi, fontSize: 12 },
  content: { marginTop: -20, backgroundColor: c.surface, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 16, paddingTop: 20 },
  demoBanner: { flexDirection: "row", gap: 8, padding: 12, borderRadius: 12, backgroundColor: c.brandTertiary, marginBottom: 16, alignItems: "flex-start" },
  demoText: { flex: 1, fontFamily: fonts.textMedium, fontSize: 13, color: c.onBrandTertiary, lineHeight: 19 },
  badgeRow: { flexDirection: "row", gap: 6, flexWrap: "wrap" },
  price: { fontFamily: fonts.display, fontSize: 28, color: c.onSurface, marginTop: 12 },
  title: { fontFamily: fonts.displaySemi, fontSize: 20, color: c.onSurfaceSecondary, marginTop: -2 },
  locRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 4 },
  loc: { fontFamily: fonts.text, fontSize: 15, color: c.muted, flex: 1 },
  stats: { flexDirection: "row", marginTop: 24, backgroundColor: c.surfaceSecondary, borderRadius: 12, paddingVertical: 16 },
  stat: { flex: 1, alignItems: "center", gap: 2, paddingHorizontal: 4 },
  statVal: { fontFamily: fonts.textSemi, fontSize: 14, color: c.onSurface, textAlign: "center" },
  statLabel: { fontFamily: fonts.text, fontSize: 12, color: c.muted },
  section: { marginTop: 32 },
  sectionTitle: { fontFamily: fonts.displaySemi, fontSize: 20, color: c.onSurface, marginBottom: 12 },
  amenGrid: { flexDirection: "row", flexWrap: "wrap", rowGap: 16 },
  amen: { width: "25%", alignItems: "center", gap: 6, paddingHorizontal: 2 },
  amenIcon: { width: 52, height: 52, borderRadius: 26, backgroundColor: c.brandTertiary, alignItems: "center", justifyContent: "center" },
  amenText: { fontFamily: fonts.text, fontSize: 12, color: c.onSurfaceSecondary, textAlign: "center" },
  locCard: { flexDirection: "row", gap: 12, alignItems: "center", padding: 16, borderRadius: 12, borderWidth: 1, borderColor: c.border },
  locCardTitle: { fontFamily: fonts.textSemi, fontSize: 16, color: c.onSurface },
  locNote: { fontFamily: fonts.text, fontSize: 13, color: c.muted },
  desc: { fontFamily: fonts.text, fontSize: 15, lineHeight: 23, color: c.onSurfaceSecondary },
  disclaimer: { fontFamily: fonts.text, fontSize: 12, lineHeight: 18, color: c.muted, marginTop: 16, padding: 12, borderRadius: 12, backgroundColor: c.surfaceSecondary },
  headerBar: { position: "absolute", left: 16, right: 16, flexDirection: "row", justifyContent: "space-between" },
  glassBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: "rgba(255,255,255,0.9)", alignItems: "center", justifyContent: "center" },
  cta: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: c.divider,
    backgroundColor: "rgba(255,255,255,0.85)",
    overflow: "hidden",
  },
  ctaPrice: { fontFamily: fonts.display, fontSize: 18, color: c.onSurface },
  ctaSub: { fontFamily: fonts.text, fontSize: 13, color: c.muted },
}));
