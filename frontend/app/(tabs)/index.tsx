import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useInfiniteQuery } from "@tanstack/react-query";
import React, { useMemo, useState } from "react";
import { ActivityIndicator, FlatList, Pressable, RefreshControl, ScrollView, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, qs } from "@/src/api";
import { BUDGETS, DEFAULT_FILTERS, Filters, FilterSheet } from "@/src/components/FilterSheet";
import { PropertyCard } from "@/src/components/PropertyCard";
import { Chip, EmptyState } from "@/src/components/ui";
import { Property, useMeta } from "@/src/data";
import { useLang } from "@/src/i18n";
import { usesNativeTabs } from "@/src/navigation";
import { fonts, makeStyles, useTheme } from "@/src/theme";

type Page = { items: Property[]; total: number; page: number; limit: number };

export default function Home() {
  const insets = useSafeAreaInsets();
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;
  const styles = useStyles();
  const { colors } = useTheme();
  const { t, pick, lang, setLang } = useLang();
  const { data: meta } = useMeta();
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [sheet, setSheet] = useState(false);

  const params = useMemo(() => {
    const b = BUDGETS[filters.purpose].find((x) => x.key === filters.budget);
    return {
      purpose: filters.purpose,
      segment: filters.segment,
      type: filters.type,
      locality: filters.locality,
      zone: filters.zone,
      min_price: b?.min,
      max_price: b?.max,
      bhk: filters.bhk,
      sort: filters.sort,
      q,
    };
  }, [filters, q]);

  const query = useInfiniteQuery({
    queryKey: ["properties", params],
    queryFn: ({ pageParam }) => api<Page>(`/properties${qs({ ...params, page: pageParam, limit: 10 })}`),
    initialPageParam: 1,
    getNextPageParam: (last) => (last.page * last.limit < last.total ? last.page + 1 : undefined),
  });

  const items = query.data?.pages.flatMap((p) => p.items) ?? [];
  const total = query.data?.pages[0]?.total ?? 0;
  const segments = meta?.categories.filter((c) => c.kind === "segment") ?? [];
  const activeCount =
    (filters.type ? 1 : 0) + (filters.budget ? 1 : 0) + filters.bhk.length + filters.locality.length + (filters.sort !== "newest" ? 1 : 0);

  const clearAll = () => {
    setFilters({ ...DEFAULT_FILTERS, purpose: filters.purpose });
    setSearch("");
    setQ("");
  };

  return (
    <View style={styles.screen}>
      {/* Sticky header */}
      <View style={[styles.header, { paddingTop: insets.top + 8 }]}>
        <View style={styles.brandRow}>
          <View>
            <Text style={styles.brand} testID="brand-title">LANDVILLA</Text>
            <Text style={styles.tagline}>{t("appTagline")}</Text>
          </View>
          <Pressable testID="lang-toggle-btn" onPress={() => setLang(lang === "en" ? "hi" : "en")} style={styles.langBtn}>
            <Text style={styles.langText}>{lang === "en" ? "हिं" : "EN"}</Text>
          </Pressable>
        </View>
        <View style={styles.searchRow}>
          <View style={styles.searchBox}>
            <Ionicons name="search" size={18} color={colors.muted} />
            <TextInput
              testID="search-input"
              value={search}
              onChangeText={setSearch}
              onSubmitEditing={() => setQ(search.trim())}
              returnKeyType="search"
              placeholder={t("searchPlaceholder")}
              placeholderTextColor={colors.muted}
              style={styles.searchInput}
            />
            {search.length > 0 && (
              <Pressable testID="search-clear-btn" hitSlop={10} onPress={() => { setSearch(""); setQ(""); }}>
                <Ionicons name="close-circle" size={18} color={colors.muted} />
              </Pressable>
            )}
          </View>
          <Pressable testID="open-filters-btn" onPress={() => setSheet(true)} style={styles.filterBtn}>
            <Ionicons name="options-outline" size={22} color={colors.onBrandPrimary} />
            {activeCount > 0 && (
              <View style={styles.filterCount}>
                <Text style={styles.filterCountText}>{activeCount}</Text>
              </View>
            )}
          </Pressable>
        </View>
        <View style={styles.segmented}>
          {(["buy", "rent"] as const).map((p) => (
            <Pressable
              key={p}
              testID={`purpose-${p}-btn`}
              onPress={() => setFilters({ ...filters, purpose: p, budget: undefined })}
              style={[styles.segBtn, filters.purpose === p && styles.segBtnOn]}
            >
              <Text style={[styles.segText, filters.purpose === p && styles.segTextOn]}>{t(p)}</Text>
            </Pressable>
          ))}
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipRow} contentContainerStyle={styles.chipRowContent}>
          <Chip label={t("all")} selected={!filters.segment} onPress={() => setFilters({ ...filters, segment: undefined, type: undefined })} testID="segment-chip-all" />
          {segments.map((s) => (
            <Chip
              key={s.slug}
              icon={s.icon}
              label={pick(s, "name")}
              selected={filters.segment === s.slug}
              onPress={() => setFilters({ ...filters, segment: filters.segment === s.slug ? undefined : s.slug, type: undefined })}
              testID={`segment-chip-${s.slug}`}
            />
          ))}
        </ScrollView>
      </View>

      <FlatList
        testID="property-list"
        data={query.isLoading || query.isError ? [] : items}
        keyExtractor={(p) => p.id}
        renderItem={({ item, index }) => <PropertyCard p={item} index={index} />}
        contentContainerStyle={{ paddingTop: 8, paddingBottom: bottomChrome + 24 }}
        onEndReached={() => query.hasNextPage && !query.isFetchingNextPage && query.fetchNextPage()}
        onEndReachedThreshold={0.4}
        refreshControl={<RefreshControl refreshing={query.isRefetching && !query.isFetchingNextPage} onRefresh={() => { query.refetch(); }} tintColor={colors.brandPrimary} />}
        ListHeaderComponent={
          <View>
            <Text style={styles.sectionTitle}>{t("zones")}</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.zoneRow}>
              {meta?.zones.map((z) => {
                const on = filters.zone === z.slug;
                const count = meta.localities.filter((l) => l.zone_id === z.id).length;
                return (
                  <Pressable
                    key={z.slug}
                    testID={`zone-card-${z.slug}`}
                    onPress={() => setFilters({ ...filters, zone: on ? undefined : z.slug, locality: [] })}
                    style={[styles.zoneCard, on && styles.zoneCardOn]}
                  >
                    <Ionicons name="navigate-circle-outline" size={20} color={on ? colors.onBrandPrimary : colors.brandPrimary} />
                    <Text style={[styles.zoneName, on && { color: colors.onBrandPrimary }]} numberOfLines={2}>{pick(z, "name")}</Text>
                    <Text style={[styles.zoneMeta, on && { color: colors.onBrandPrimary }]}>{count} {lang === "hi" ? "इलाके" : "localities"}</Text>
                  </Pressable>
                );
              })}
            </ScrollView>
            {!query.isLoading && !query.isError && (
              <View style={styles.resultsRow}>
                <Text style={styles.results} testID="results-count">
                  {total} {total === 1 ? t("property") : t("properties")}
                </Text>
                {(activeCount > 0 || !!filters.zone || !!q) && (
                  <Pressable onPress={() => { clearAll(); setFilters((f) => ({ ...f, zone: undefined, segment: undefined })); }} testID="clear-all-btn" hitSlop={8}>
                    <Text style={styles.clear}>{t("clearFilters")}</Text>
                  </Pressable>
                )}
              </View>
            )}
          </View>
        }
        ListEmptyComponent={
          query.isLoading ? (
            <View>{[0, 1].map((i) => <View key={i} style={styles.skeleton} />)}</View>
          ) : query.isError ? (
            <EmptyState icon="cloud-offline-outline" title={t("loadError")} cta={t("retry")} onPress={() => query.refetch()} testID="home-error" />
          ) : (
            <EmptyState icon="home-outline" title={t("noResults")} cta={t("clearFilters")} onPress={() => { clearAll(); setFilters((f) => ({ ...f, zone: undefined, segment: undefined })); }} testID="home-empty" />
          )
        }
        ListFooterComponent={query.isFetchingNextPage ? <ActivityIndicator color={colors.brandPrimary} style={{ marginVertical: 16 }} /> : undefined}
      />

      <FilterSheet visible={sheet} onClose={() => setSheet(false)} value={filters} meta={meta} onApply={(f) => { setFilters(f); setSheet(false); }} />
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  header: { backgroundColor: c.surface, borderBottomWidth: 1, borderBottomColor: c.divider },
  brandRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 16 },
  brand: { fontFamily: fonts.display, fontSize: 24, color: c.brandPrimary, letterSpacing: 1.5 },
  tagline: { fontFamily: fonts.text, fontSize: 13, color: c.muted, marginTop: -4 },
  langBtn: { minWidth: 44, height: 44, borderRadius: 22, borderWidth: 1, borderColor: c.border, alignItems: "center", justifyContent: "center", paddingHorizontal: 12 },
  langText: { fontFamily: fonts.textSemi, fontSize: 15, color: c.onSurface },
  searchRow: { flexDirection: "row", gap: 8, paddingHorizontal: 16, marginTop: 12 },
  searchBox: { flex: 1, height: 48, borderRadius: 12, backgroundColor: c.surfaceTertiary, flexDirection: "row", alignItems: "center", paddingHorizontal: 12, gap: 8 },
  searchInput: { flex: 1, height: 48, fontFamily: fonts.text, fontSize: 15, color: c.onSurface },
  filterBtn: { width: 48, height: 48, borderRadius: 12, backgroundColor: c.brandPrimary, alignItems: "center", justifyContent: "center" },
  filterCount: { position: "absolute", top: 4, right: 4, minWidth: 18, height: 18, borderRadius: 9, backgroundColor: c.surfaceInverse, alignItems: "center", justifyContent: "center", paddingHorizontal: 4 },
  filterCountText: { color: c.onSurfaceInverse, fontSize: 11, fontFamily: fonts.textSemi },
  segmented: { flexDirection: "row", marginHorizontal: 16, marginTop: 12, backgroundColor: c.surfaceTertiary, borderRadius: 12, padding: 4 },
  segBtn: { flex: 1, height: 36, borderRadius: 8, alignItems: "center", justifyContent: "center" },
  segBtnOn: { backgroundColor: c.surface, shadowColor: "#000", shadowOpacity: 0.08, shadowRadius: 4, shadowOffset: { width: 0, height: 1 }, elevation: 1 },
  segText: { fontFamily: fonts.textMedium, fontSize: 15, color: c.onSurfaceTertiary },
  segTextOn: { color: c.brandPrimary, fontFamily: fonts.textSemi },
  chipRow: { height: 56, flexGrow: 0 },
  chipRowContent: { gap: 8, paddingHorizontal: 16, alignItems: "center" },
  sectionTitle: { fontFamily: fonts.displaySemi, fontSize: 18, color: c.onSurface, paddingHorizontal: 16, marginTop: 8, marginBottom: 12 },
  zoneRow: { paddingHorizontal: 16, gap: 12 },
  zoneCard: { width: 140, padding: 12, borderRadius: 12, backgroundColor: c.surface, borderWidth: 1, borderColor: c.border, gap: 4 },
  zoneCardOn: { backgroundColor: c.brandPrimary, borderColor: c.brandPrimary },
  zoneName: { fontFamily: fonts.textSemi, fontSize: 14, color: c.onSurface, lineHeight: 18, minHeight: 36 },
  zoneMeta: { fontFamily: fonts.text, fontSize: 12, color: c.muted },
  resultsRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 16, marginTop: 24, marginBottom: 12 },
  results: { fontFamily: fonts.textSemi, fontSize: 15, color: c.onSurfaceSecondary },
  clear: { fontFamily: fonts.textSemi, fontSize: 14, color: c.brandPrimary },
  skeleton: { height: 300, borderRadius: 20, marginHorizontal: 16, marginBottom: 16, backgroundColor: c.surfaceTertiary },
}));
