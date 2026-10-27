import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { ActivityIndicator, ScrollView, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Sheet } from "@/src/components/Sheet";
import { useToast } from "@/src/components/Toast";
import { Badge, Button, EmptyState, ScreenHeader } from "@/src/components/ui";
import { fonts, makeStyles, useTheme } from "@/src/theme";

type Act = { id: string; action: "dismiss" | "remove_listing" | "suspend_user" } | null;

export default function AdminReports() {
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const { user } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const [act, setAct] = useState<Act>(null);
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");
  const q = useQuery({ queryKey: ["admin-reports"], queryFn: () => api<{ items: any[]; deletion_requests: any[] }>("/admin/reports"), enabled: user?.role === "admin" });
  const m = useMutation({
    mutationFn: () => api(`/admin/reports/${act!.id}/resolve`, { method: "POST", body: { action: act!.action, note } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-reports"] }); setAct(null); toast.show("Report resolved", "success"); },
    onError: (e: any) => setErr(e.message),
  });
  const closeReq = useMutation({
    mutationFn: (p: { id: string; status: string }) => api(`/admin/deletion-requests/${p.id}`, { method: "POST", body: { status: p.status, note: `Marked ${p.status} by admin` } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-reports"] }).then(() => toast.show("Request updated", "success")),
    onError: (e: any) => toast.show(e.message, "error"),
  });
  if (user?.role !== "admin") return <View style={[styles.screen, { paddingTop: insets.top + 40 }]}><EmptyState icon="lock-closed-outline" title="Admin access required" cta="Go back" onPress={() => router.back()} testID="admin-denied" /></View>;
  const open = (id: string, action: NonNullable<Act>["action"]) => { setNote(""); setErr(""); setAct({ id, action }); };

  return (
    <View style={styles.screen}>
      <ScreenHeader title="Reports" onBack={() => router.back()} topInset={insets.top} />
      {q.isLoading ? <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 40 }} /> : (
        <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: insets.bottom + 24 }}>
          {q.data?.items.length === 0 && <EmptyState icon="shield-checkmark-outline" title="No open reports" testID="reports-empty" />}
          {q.data?.items.map((r) => (
            <View key={r.id} style={styles.card} testID={`report-${r.id}`}>
              <View style={{ flexDirection: "row", gap: 6 }}><Badge label={r.target_type.toUpperCase()} kind="muted" /><Badge label={r.reason.replace(/_/g, " ")} kind="demo" /></View>
              <Text style={styles.title}>{r.target_label}</Text>
              {!!r.note && <Text style={styles.meta}>"{r.note}"</Text>}
              <Text style={styles.meta}>{new Date(r.created_at).toLocaleString("en-IN")}</Text>
              <View style={{ flexDirection: "row", gap: 8, flexWrap: "wrap" }}>
                <Button label="Dismiss" variant="outline" onPress={() => open(r.id, "dismiss")} testID={`report-dismiss-${r.id}`} />
                {r.target_type === "property" && <Button label="Remove listing" onPress={() => open(r.id, "remove_listing")} testID={`report-remove-${r.id}`} />}
                {r.reported_user_id && <Button label="Suspend user" onPress={() => open(r.id, "suspend_user")} testID={`report-suspend-${r.id}`} />}
              </View>
            </View>
          ))}
          <Text style={styles.section}>Account deletion requests (web form)</Text>
          {q.data?.deletion_requests.length === 0 && <Text style={styles.meta}>None open.</Text>}
          {q.data?.deletion_requests.map((d) => (
            <View key={d.id} style={styles.card} testID={`deletion-request-${d.id}`}>
              <Text style={styles.title}>{d.email}</Text>
              <Text style={styles.meta}>{d.reason || "No reason"} · {new Date(d.created_at).toLocaleDateString("en-IN")}</Text>
              <Text style={styles.meta}>Verify ownership by email, then delete the account.</Text>
              <View style={{ flexDirection: "row", gap: 8 }}>
                <Button label="Done" disabled={closeReq.isPending} onPress={() => closeReq.mutate({ id: d.id, status: "completed" })} testID={`deletion-complete-${d.id}`} style={{ flex: 1 }} />
                <Button label="Reject" variant="outline" disabled={closeReq.isPending} onPress={() => closeReq.mutate({ id: d.id, status: "rejected" })} testID={`deletion-reject-${d.id}`} style={{ flex: 1 }} />
              </View>
            </View>
          ))}
        </ScrollView>
      )}
      <Sheet visible={!!act} onClose={() => setAct(null)} title="Resolve report" testID="resolve-sheet"
        footer={<Button label="Confirm" onPress={() => m.mutate()} loading={m.isPending} testID="resolve-confirm-btn" />}>
        <View style={{ paddingHorizontal: 16, paddingBottom: 16, gap: 8 }}>
          <Text style={styles.meta}>Action: {act?.action.replace("_", " ")}</Text>
          <TextInput testID="resolve-note-input" value={note} onChangeText={setNote} multiline placeholder="Resolution note (required)" placeholderTextColor={colors.muted} style={styles.input} />
          {!!err && <Text style={{ color: colors.error }} testID="resolve-error">{err}</Text>}
        </View>
      </Sheet>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  card: { backgroundColor: c.surface, borderRadius: 12, padding: 12, borderWidth: 1, borderColor: c.border, gap: 6 },
  title: { fontFamily: fonts.textSemi, fontSize: 15, color: c.onSurface },
  meta: { fontFamily: fonts.text, fontSize: 13, color: c.onSurfaceTertiary },
  section: { fontFamily: fonts.displaySemi, fontSize: 18, color: c.onSurface, marginTop: 12 },
  input: { minHeight: 80, borderRadius: 12, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, padding: 12, fontFamily: fonts.text, fontSize: 15, color: c.onSurface, textAlignVertical: "top" },
}));
