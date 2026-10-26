import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { ActivityIndicator, FlatList, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Sheet } from "@/src/components/Sheet";
import { useToast } from "@/src/components/Toast";
import { Badge, Button, Chip, EmptyState } from "@/src/components/ui";
import { useMeta } from "@/src/data";
import { fonts, makeStyles, useTheme } from "@/src/theme";

type Loc = {
  id: string; slug: string; name_en: string; name_hi: string; aliases: string[]; zone_id: string | null; parent_id: string | null;
  is_active: boolean; source: string; verification_status: string; last_verified_at: string | null; zone_assignment: string;
  merged_into: string | null; listing_count: number;
};

type Mode = { kind: "create" } | { kind: "edit"; loc: Loc } | { kind: "verify"; loc: Loc } | { kind: "merge"; loc: Loc } | { kind: "deactivate"; loc: Loc } | null;

export default function AdminLocalities() {
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const { user } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const { data: meta } = useMeta();
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState<Mode>(null);
  const q = useQuery({ queryKey: ["admin-localities"], queryFn: () => api<{ items: Loc[] }>("/admin/localities"), enabled: user?.role === "admin" });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["admin-localities"] });
    qc.invalidateQueries({ queryKey: ["meta"] });
    qc.invalidateQueries({ queryKey: ["properties"] });
  };
  const action = useMutation({
    mutationFn: (p: { path: string; method?: string; body?: any }) => api(p.path, { method: p.method ?? "POST", body: p.body }),
    onSuccess: () => { refresh(); setMode(null); toast.show("Saved", "success"); },
    onError: (e: any) => toast.show(e.message, "error"),
  });

  const zoneName = (id: string | null) => meta?.zones.find((z) => z.id === id)?.name_en ?? "No zone";
  const items = (q.data?.items ?? []).filter((l) => {
    const s = search.trim().toLowerCase();
    return !s || l.name_en.toLowerCase().includes(s) || l.name_hi.includes(s) || l.aliases.some((a) => a.toLowerCase().includes(s));
  });

  if (user?.role !== "admin") {
    return (
      <View style={[styles.screen, { paddingTop: insets.top + 40 }]}>
        <EmptyState icon="lock-closed-outline" title="Admin access required" cta="Go back" onPress={() => router.back()} testID="admin-denied" />
      </View>
    );
  }

  return (
    <View style={styles.screen}>
      <View style={[styles.header, { paddingTop: insets.top + 8 }]}>
        <View style={styles.headRow}>
          <Pressable testID="admin-back-btn" onPress={() => router.back()} style={styles.iconBtn}>
            <Ionicons name="chevron-back" size={24} color={colors.onSurface} />
          </Pressable>
          <Text style={styles.title}>Localities</Text>
          <Pressable testID="admin-add-locality-btn" onPress={() => setMode({ kind: "create" })} style={[styles.iconBtn, styles.addBtn]}>
            <Ionicons name="add" size={24} color={colors.onBrandPrimary} />
          </Pressable>
        </View>
        <View style={styles.searchBox}>
          <Ionicons name="search" size={18} color={colors.muted} />
          <TextInput testID="admin-locality-search" value={search} onChangeText={setSearch} placeholder="Search name or alias" placeholderTextColor={colors.muted} style={styles.searchInput} />
        </View>
      </View>
      {q.isLoading ? (
        <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={items}
          keyExtractor={(l) => l.id}
          contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: insets.bottom + 24 }}
          ListHeaderComponent={<Text style={styles.count}>{q.data?.items.length ?? 0} records · {q.data?.items.filter((l) => l.verification_status === "verified").length ?? 0} verified</Text>}
          renderItem={({ item: l }) => (
            <View style={[styles.card, !l.is_active && { opacity: 0.6 }]} testID={`admin-locality-${l.slug}`}>
              <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.locName}>{l.name_en} · {l.name_hi}</Text>
                  <Text style={styles.locMeta}>{zoneName(l.zone_id)} ({l.zone_assignment}) · {l.listing_count} listings</Text>
                  {l.aliases.length > 0 && <Text style={styles.locMeta}>Aliases: {l.aliases.join(", ")}</Text>}
                  <Text style={styles.locMeta} numberOfLines={1}>Source: {l.source}</Text>
                </View>
                <View style={{ gap: 4, alignItems: "flex-end" }}>
                  <Badge label={l.verification_status.toUpperCase()} kind={l.verification_status === "verified" ? "verified" : "muted"} />
                  {!l.is_active && <Badge label={l.merged_into ? "MERGED" : "INACTIVE"} kind="demo" />}
                </View>
              </View>
              {!l.merged_into && (
                <View style={styles.actions}>
                  <Chip label="Edit" icon="create-outline" onPress={() => setMode({ kind: "edit", loc: l })} testID={`admin-edit-${l.slug}`} />
                  {l.verification_status !== "verified" && <Chip label="Verify" icon="shield-checkmark-outline" onPress={() => setMode({ kind: "verify", loc: l })} testID={`admin-verify-${l.slug}`} />}
                  {l.is_active && <Chip label="Merge" icon="git-merge-outline" onPress={() => setMode({ kind: "merge", loc: l })} testID={`admin-merge-${l.slug}`} />}
                  <Chip
                    label={l.is_active ? "Deactivate" : "Activate"}
                    icon={l.is_active ? "pause-circle-outline" : "play-circle-outline"}
                    onPress={() => (l.is_active ? setMode({ kind: "deactivate", loc: l }) : action.mutate({ path: `/admin/localities/${l.id}/activate` }))}
                    testID={`admin-toggle-${l.slug}`}
                  />
                </View>
              )}
            </View>
          )}
        />
      )}
      <LocalityForm mode={mode} onClose={() => setMode(null)} meta={meta} all={q.data?.items ?? []} loading={action.isPending} onSubmit={(p) => action.mutate(p)} />
    </View>
  );
}

function LocalityForm({ mode, onClose, meta, all, loading, onSubmit }: { mode: Mode; onClose: () => void; meta: any; all: Loc[]; loading: boolean; onSubmit: (p: { path: string; method?: string; body?: any }) => void }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const loc = mode && mode.kind !== "create" ? mode.loc : null;
  const [nameEn, setNameEn] = useState("");
  const [nameHi, setNameHi] = useState("");
  const [aliases, setAliases] = useState("");
  const [zone, setZone] = useState<string | null>(null);
  const [source, setSource] = useState("");
  const [target, setTarget] = useState<string | null>(null);
  const [err, setErr] = useState("");

  React.useEffect(() => {
    setNameEn(loc?.name_en ?? "");
    setNameHi(loc?.name_hi ?? "");
    setAliases(loc?.aliases.join(", ") ?? "");
    setZone(loc?.zone_id ?? null);
    setSource("");
    setTarget(null);
    setErr("");
  }, [mode, loc]);

  if (!mode) return null;
  const title = { create: "Add locality", edit: "Edit locality", verify: "Verify locality", merge: "Merge locality", deactivate: "Deactivate locality" }[mode.kind];
  const saveLabel = { create: "Create", edit: "Save changes", verify: "Mark verified", merge: "Merge", deactivate: "Deactivate" }[mode.kind];

  const submit = () => {
    setErr("");
    const aliasArr = aliases.split(",").map((a) => a.trim()).filter(Boolean);
    if (mode.kind === "create" || mode.kind === "edit") {
      if (nameEn.trim().length < 2 || !nameHi.trim()) return setErr("English and Hindi names are required");
      const body = { name_en: nameEn.trim(), name_hi: nameHi.trim(), aliases: aliasArr, zone_id: zone };
      if (mode.kind === "create") onSubmit({ path: "/admin/localities", body: { ...body, source: source.trim() || "admin_entry" } });
      else onSubmit({ path: `/admin/localities/${mode.loc.id}`, method: "PATCH", body });
    } else if (mode.kind === "verify") {
      if (source.trim().length < 3) return setErr("Enter the verification source (e.g. municipal ward list, site visit)");
      onSubmit({ path: `/admin/localities/${mode.loc.id}/verify`, body: { source: source.trim() } });
    } else if (mode.kind === "merge") {
      if (!target) return setErr("Choose the locality to merge into");
      onSubmit({ path: "/admin/localities/merge", body: { source_id: mode.loc.id, target_id: target } });
    } else if (mode.kind === "deactivate") {
      onSubmit({ path: `/admin/localities/${mode.loc.id}/deactivate` });
    }
  };

  return (
    <Sheet visible={!!mode} onClose={onClose} title={title} testID="admin-locality-sheet" footer={<Button label={saveLabel} onPress={submit} loading={loading} testID="admin-locality-save-btn" />}>
      <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 16 }} keyboardShouldPersistTaps="handled">
        {(mode.kind === "create" || mode.kind === "edit") && (
          <>
            <Text style={styles.label}>Name (English)</Text>
            <TextInput testID="admin-name-en-input" value={nameEn} onChangeText={setNameEn} style={styles.input} placeholderTextColor={colors.muted} />
            <Text style={styles.label}>Name (Hindi)</Text>
            <TextInput testID="admin-name-hi-input" value={nameHi} onChangeText={setNameHi} style={styles.input} placeholderTextColor={colors.muted} />
            <Text style={styles.label}>Aliases (comma separated)</Text>
            <TextInput testID="admin-aliases-input" value={aliases} onChangeText={setAliases} style={styles.input} placeholderTextColor={colors.muted} />
            <Text style={styles.label}>Zone</Text>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
              <Chip label="No zone" selected={!zone} onPress={() => setZone(null)} testID="admin-zone-none" />
              {meta?.zones.map((z: any) => (
                <Chip key={z.id} label={z.name_en} selected={zone === z.id} onPress={() => setZone(z.id)} testID={`admin-zone-${z.slug}`} />
              ))}
            </View>
            {mode.kind === "create" && (
              <>
                <Text style={styles.label}>Source</Text>
                <TextInput testID="admin-source-input" value={source} onChangeText={setSource} style={styles.input} placeholder="Where did this name come from?" placeholderTextColor={colors.muted} />
              </>
            )}
          </>
        )}
        {mode.kind === "verify" && (
          <>
            <Text style={styles.help}>Only verify after confirming the locality from an authoritative source. Record that source below.</Text>
            <Text style={styles.label}>Verification source</Text>
            <TextInput testID="admin-verify-source-input" value={source} onChangeText={setSource} style={styles.input} placeholder="e.g. UMC ward list 2026, field visit" placeholderTextColor={colors.muted} />
          </>
        )}
        {mode.kind === "merge" && (
          <>
            <Text style={styles.help}>"{mode.loc.name_en}" will be deactivated. Its listings and aliases move to the locality you pick.</Text>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
              {all.filter((l) => l.is_active && l.id !== mode.loc.id).map((l) => (
                <Chip key={l.id} label={l.name_en} selected={target === l.id} onPress={() => setTarget(l.id)} testID={`admin-merge-target-${l.slug}`} />
              ))}
            </View>
          </>
        )}
        {mode.kind === "deactivate" && (
          <Text style={styles.help}>"{mode.loc.name_en}" will be hidden from customer search and filters ({mode.loc.listing_count} listings). You can activate it again later.</Text>
        )}
        {!!err && <Text style={styles.err} testID="admin-form-error">{err}</Text>}
      </ScrollView>
    </Sheet>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  header: { backgroundColor: c.surface, paddingHorizontal: 16, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: c.divider, gap: 12 },
  headRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  iconBtn: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center" },
  addBtn: { backgroundColor: c.brandPrimary },
  title: { fontFamily: fonts.display, fontSize: 22, color: c.onSurface },
  searchBox: { height: 44, borderRadius: 12, backgroundColor: c.surfaceTertiary, flexDirection: "row", alignItems: "center", paddingHorizontal: 12, gap: 8 },
  searchInput: { flex: 1, height: 44, fontFamily: fonts.text, fontSize: 15, color: c.onSurface },
  count: { fontFamily: fonts.textMedium, fontSize: 13, color: c.muted },
  card: { backgroundColor: c.surface, borderRadius: 12, padding: 12, borderWidth: 1, borderColor: c.border },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 },
  locName: { fontFamily: fonts.textSemi, fontSize: 15, color: c.onSurface },
  locMeta: { fontFamily: fonts.text, fontSize: 12, color: c.muted, marginTop: 2 },
  label: { fontFamily: fonts.textSemi, fontSize: 14, color: c.onSurfaceSecondary, marginTop: 16, marginBottom: 8 },
  input: { height: 48, borderRadius: 12, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, paddingHorizontal: 12, fontFamily: fonts.text, fontSize: 15, color: c.onSurface },
  help: { fontFamily: fonts.text, fontSize: 14, color: c.onSurfaceTertiary, lineHeight: 20 },
  err: { color: c.error, fontFamily: fonts.textMedium, marginTop: 12 },
}));
