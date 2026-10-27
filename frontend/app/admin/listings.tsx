import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { ActivityIndicator, FlatList, ScrollView, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, fileUrl } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Sheet } from "@/src/components/Sheet";
import { useToast } from "@/src/components/Toast";
import { Badge, Button, Chip, EmptyState, ScreenHeader } from "@/src/components/ui";
import { formatPrice } from "@/src/data";
import { fonts, makeStyles, useTheme } from "@/src/theme";

const TABS = [["pending_review", "Pending"], ["changes_requested", "Changes"], ["active", "Live"], ["rejected", "Rejected"]] as const;
type Action = { kind: "approve" | "reject" | "request-changes"; item: any } | null;

export default function AdminListings() {
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const { user } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const [status, setStatus] = useState<string>("pending_review");
  const [action, setAction] = useState<Action>(null);
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");
  const q = useQuery({ queryKey: ["admin-listings", status], queryFn: () => api<{ items: any[]; counts: Record<string, number> }>(`/admin/listings?status=${status}`), enabled: user?.role === "admin" });
  const m = useMutation({
    mutationFn: () => api(`/admin/listings/${action!.item.id}/${action!.kind}`, { method: "POST", body: { note } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-listings"] }); qc.invalidateQueries({ queryKey: ["properties"] }); setAction(null); toast.show("Listing updated", "success"); },
    onError: (e: any) => setErr(e.message),
  });

  if (user?.role !== "admin") return <View style={[styles.screen, { paddingTop: insets.top + 40 }]}><EmptyState icon="lock-closed-outline" title="Admin access required" cta="Go back" onPress={() => router.back()} testID="admin-denied" /></View>;

  const open = (kind: NonNullable<Action>["kind"], item: any) => { setNote(""); setErr(""); setAction({ kind, item }); };

  return (
    <View style={styles.screen}>
      <View style={styles.headWrap}>
        <ScreenHeader title="Approval queue" onBack={() => router.back()} topInset={insets.top} />
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ height: 56, flexGrow: 0 }} contentContainerStyle={{ gap: 8, paddingHorizontal: 16, alignItems: "center" }}>
          {TABS.map(([k, label]) => (
            <Chip key={k} label={`${label} ${q.data?.counts?.[k] ?? 0}`} selected={status === k} onPress={() => setStatus(k)} testID={`admin-listings-tab-${k}`} />
          ))}
        </ScrollView>
      </View>
      {q.isLoading ? <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 40 }} /> : (
        <FlatList
          data={q.data?.items ?? []}
          keyExtractor={(p) => p.id}
          contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: insets.bottom + 24 }}
          ListEmptyComponent={<EmptyState icon="checkmark-done-outline" title="Nothing here" testID="admin-listings-empty" />}
          renderItem={({ item: p }) => (
            <View style={styles.card} testID={`admin-listing-${p.id}`}>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6 }}>
                {p.images.map((u: string, i: number) => <Image key={i} source={{ uri: fileUrl(u) }} style={styles.img} contentFit="cover" />)}
              </ScrollView>
              <Text style={styles.title}>{p.title_en}</Text>
              <Text style={styles.sub}>{formatPrice(p.price, p.purpose, "en")} · {p.locality?.name_en} · {p.type} · {p.area_sqft} sq.ft{p.bhk ? ` · ${p.bhk} BHK` : ""}</Text>
              <Text style={styles.meta}>By {p.owner?.name} ({p.owner?.email}) as <Text style={{ fontFamily: fonts.textSemi }}>{p.posted_by_role}</Text></Text>
              <Text style={styles.meta}>Declaration: {p.owner_declaration?.accepted ? `accepted (${p.owner_declaration.version})` : "missing"}</Text>
              <Text style={styles.desc} numberOfLines={4}>{p.description_en}</Text>
              {p.duplicate_flags?.length > 0 && (
                <View style={styles.dup} testID={`dup-flags-${p.id}`}>
                  <View style={{ flexDirection: "row", gap: 6, alignItems: "center" }}>
                    <Ionicons name="warning-outline" size={18} color={colors.error} />
                    <Text style={styles.dupTitle}>Possible duplicate ({p.duplicate_flags.length})</Text>
                  </View>
                  {p.duplicate_flags.map((d: any) => <Text key={d.property_id} style={styles.dupText}>• {d.property_id}: {d.reasons.join(", ")}</Text>)}
                </View>
              )}
              {p.moderation?.note ? <Text style={styles.meta}>Last note: {p.moderation.note}</Text> : null}
              <View style={styles.actions}>
                {p.listing_status !== "active" && <Badge label={p.listing_status} kind="muted" />}
              </View>
              {p.listing_status !== "rejected" && (
                <View style={styles.actions}>
                  {p.listing_status !== "active" && <Button label="Approve" icon="checkmark" onPress={() => open("approve", p)} testID={`approve-${p.id}`} style={{ flex: 1 }} />}
                  <Button label="Changes" variant="outline" onPress={() => open("request-changes", p)} testID={`changes-${p.id}`} style={{ flex: 1 }} />
                  <Button label="Reject" variant="outline" onPress={() => open("reject", p)} testID={`reject-${p.id}`} style={{ flex: 1 }} />
                </View>
              )}
            </View>
          )}
        />
      )}
      <Sheet visible={!!action} onClose={() => setAction(null)} title={action?.kind === "approve" ? "Approve & publish" : action?.kind === "reject" ? "Reject listing" : "Request changes"} testID="moderation-sheet"
        footer={<Button label={action?.kind === "approve" ? "Approve" : action?.kind === "reject" ? "Reject" : "Send request"} onPress={() => m.mutate()} loading={m.isPending} testID="moderation-confirm-btn" />}>
        <View style={{ paddingHorizontal: 16, paddingBottom: 16, gap: 8 }}>
          <Text style={styles.meta}>{action?.item?.title_en}</Text>
          {action?.kind === "approve" && <Text style={styles.meta}>Approving publishes the listing. It does not mean title or legal status is verified.</Text>}
          <TextInput testID="moderation-note-input" value={note} onChangeText={setNote} multiline placeholder={action?.kind === "approve" ? "Note (optional)" : "Reason shown to the lister (required)"} placeholderTextColor={colors.muted} style={styles.input} />
          {!!err && <Text style={styles.err} testID="moderation-error">{err}</Text>}
        </View>
      </Sheet>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  headWrap: { backgroundColor: c.surface, borderBottomWidth: 1, borderBottomColor: c.divider },
  card: { backgroundColor: c.surface, borderRadius: 12, padding: 12, borderWidth: 1, borderColor: c.border, gap: 6 },
  img: { width: 120, height: 90, borderRadius: 8, backgroundColor: c.surfaceTertiary },
  title: { fontFamily: fonts.textSemi, fontSize: 16, color: c.onSurface, marginTop: 4 },
  sub: { fontFamily: fonts.textMedium, fontSize: 13, color: c.brandPrimary },
  meta: { fontFamily: fonts.text, fontSize: 13, color: c.onSurfaceTertiary },
  desc: { fontFamily: fonts.text, fontSize: 13, color: c.onSurfaceSecondary, lineHeight: 19 },
  dup: { padding: 10, borderRadius: 8, borderWidth: 1, borderColor: c.error, gap: 4 },
  dupTitle: { fontFamily: fonts.textSemi, fontSize: 14, color: c.error },
  dupText: { fontFamily: fonts.text, fontSize: 12, color: c.onSurfaceSecondary },
  actions: { flexDirection: "row", gap: 8, flexWrap: "wrap" },
  input: { minHeight: 90, borderRadius: 12, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, padding: 12, fontFamily: fonts.text, fontSize: 15, color: c.onSurface, textAlignVertical: "top" },
  err: { color: c.error, fontFamily: fonts.textMedium },
}));
