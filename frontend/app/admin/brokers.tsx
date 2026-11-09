import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { ActivityIndicator, FlatList, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";

import { api, fileUrl, getApiToken } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Sheet } from "@/src/components/Sheet";
import { useToast } from "@/src/components/Toast";
import { Badge, Button, Chip, EmptyState, ScreenHeader } from "@/src/components/ui";
import { fonts, makeStyles, useTheme } from "@/src/theme";

const TABS = ["pending", "approved", "rejected", "suspended"] as const;
type Action = { kind: "approve" | "reject" | "suspend"; item: any } | null;

export default function AdminBrokers() {
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const { user } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const [status, setStatus] = useState<string>("pending");
  const [action, setAction] = useState<Action>(null);
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");
  const q = useQuery({ queryKey: ["admin-brokers", status], queryFn: () => api<{ items: any[]; counts: Record<string, number> }>(`/admin/brokers?status=${status}`), enabled: user?.role === "admin" });
  const m = useMutation({
    mutationFn: () => api(`/admin/brokers/${action!.item.user_id}/${action!.kind}`, { method: "POST", body: { note } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-brokers"] }); setAction(null); toast.show("Broker updated", "success"); },
    onError: (e: any) => setErr(e.message),
  });

  if (user?.role !== "admin") return <View style={[styles.screen, { paddingTop: insets.top + 40 }]}><EmptyState icon="lock-closed-outline" title="Admin access required" cta="Go back" onPress={() => router.back()} testID="admin-denied" /></View>;

  const openDoc = async (doc: { url: string; id: string; content_type?: string }) => {
    const url = doc?.url || "";

    if (!url.startsWith("/api/files/") || url.startsWith("//")) {
      toast.show("Invalid document URL", "error");
      return;
    }

    if (Platform.OS === "web") {
      const webUrl = fileUrl(url);
      if (webUrl) window.open(webUrl, "_blank", "noopener,noreferrer");
      else toast.show("Backend URL is not configured", "error");
      return;
    }

    const token = getApiToken();
    if (!token) {
      toast.show("Please sign in again to view this document", "error");
      return;
    }

    const downloadUrl = fileUrl(url);
    const cacheDir = FileSystem.cacheDirectory;

    if (!downloadUrl || !cacheDir) {
      toast.show("Document download is unavailable", "error");
      return;
    }

    const mimeType = doc.content_type || "application/octet-stream";
    const extensionByType: Record<string, string> = {
      "application/pdf": "pdf",
      "image/jpeg": "jpg",
      "image/png": "png",
      "image/webp": "webp",
    };

    const extension = extensionByType[mimeType];
    if (!extension) {
      toast.show("Unsupported document type", "error");
      return;
    }

    const localUri = `${cacheDir}landvilla-broker-${doc.id}.${extension}`;

    try {
      const result = await FileSystem.downloadAsync(downloadUrl, localUri, {
        headers: { Authorization: `Bearer ${token}` },

      });

      if (result.status < 200 || result.status >= 300) {
        throw new Error(`Document download failed (${result.status})`);
      }

      if (!(await Sharing.isAvailableAsync())) {
        throw new Error("File sharing is not available on this device");
      }

      await Sharing.shareAsync(result.uri, {
        mimeType,
        dialogTitle: "Open broker verification document",
      });
    } catch (error: any) {
      console.error("Broker document download/open failed:", error);
      toast.show(error?.message || "Unable to open document", "error");
    }
  };

  return (
    <View style={styles.screen}>
      <View style={styles.headWrap}>
        <ScreenHeader title="Broker verification" onBack={() => router.back()} topInset={insets.top} />
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ height: 56, flexGrow: 0 }} contentContainerStyle={{ gap: 8, paddingHorizontal: 16, alignItems: "center" }}>
          {TABS.map((k) => <Chip key={k} label={`${k[0].toUpperCase()}${k.slice(1)} ${q.data?.counts?.[k] ?? 0}`} selected={status === k} onPress={() => setStatus(k)} testID={`admin-brokers-tab-${k}`} />)}
        </ScrollView>
      </View>
      {q.isLoading ? <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 40 }} /> : (
        <FlatList
          data={q.data?.items ?? []}
          keyExtractor={(b) => b.user_id}
          contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: insets.bottom + 24 }}
          ListEmptyComponent={<EmptyState icon="briefcase-outline" title="No broker requests" testID="admin-brokers-empty" />}
          renderItem={({ item: b }) => (
            <View style={styles.card} testID={`admin-broker-${b.user_id}`}>
              <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                <Text style={styles.title}>{b.full_name}</Text>
                <Badge label={b.status.toUpperCase()} kind={b.status === "approved" ? "verified" : b.status === "pending" ? "muted" : "demo"} />
              </View>
              <Text style={styles.meta}>{b.email} · +91 {b.phone}</Text>
              {!!b.firm_name && <Text style={styles.meta}>Firm: {b.firm_name}</Text>}
              <Text style={styles.meta}>RERA: {b.rera_number || "not provided"} ({b.rera_status})</Text>
              {b.admin_note && <Text style={styles.meta}>Note: {b.admin_note}</Text>}
              {b.documents.map((d: any) => (
                <Pressable key={d.id} style={styles.doc} onPress={() => openDoc(d)} testID={`broker-doc-${d.id}`}>
                  <Ionicons name="document-attach-outline" size={18} color={colors.brandPrimary} />
                  <Text style={styles.docText} numberOfLines={1}>{d.name || d.id}</Text>
                  <Ionicons name="open-outline" size={16} color={colors.muted} />
                </Pressable>
              ))}
              <View style={styles.actions}>
                {(b.status === "pending" || b.status === "suspended") && <Button label="Approve" icon="checkmark" onPress={() => { setNote(""); setErr(""); setAction({ kind: "approve", item: b }); }} testID={`broker-approve-${b.user_id}`} style={{ flex: 1 }} />}
                {b.status === "pending" && <Button label="Reject" variant="outline" onPress={() => { setNote(""); setErr(""); setAction({ kind: "reject", item: b }); }} testID={`broker-reject-${b.user_id}`} style={{ flex: 1 }} />}
                {b.status === "approved" && <Button label="Suspend" variant="outline" onPress={() => { setNote(""); setErr(""); setAction({ kind: "suspend", item: b }); }} testID={`broker-suspend-${b.user_id}`} style={{ flex: 1 }} />}
              </View>
            </View>
          )}
        />
      )}
      <Sheet visible={!!action} onClose={() => setAction(null)} title={`${action?.kind === "approve" ? "Approve" : action?.kind === "reject" ? "Reject" : "Suspend"} broker`} testID="broker-action-sheet"
        footer={<Button label="Confirm" onPress={() => m.mutate()} loading={m.isPending} testID="broker-action-confirm-btn" />}>
        <View style={{ paddingHorizontal: 16, paddingBottom: 16, gap: 8 }}>
          <Text style={styles.meta}>{action?.item?.full_name}</Text>
          {action?.kind === "approve" && <Text style={styles.meta}>Identity approval only. RERA status remains as recorded unless separately verified.</Text>}
          {action?.kind === "suspend" && <Text style={styles.meta}>Suspending unpublishes this broker&apos;s live broker listings.</Text>}
          <TextInput testID="broker-action-note" value={note} onChangeText={setNote} multiline placeholder={action?.kind === "approve" ? "Note (optional)" : "Reason (required)"} placeholderTextColor={colors.muted} style={styles.input} />
          {!!err && <Text style={styles.err} testID="broker-action-error">{err}</Text>}
        </View>
      </Sheet>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  headWrap: { backgroundColor: c.surface, borderBottomWidth: 1, borderBottomColor: c.divider },
  card: { backgroundColor: c.surface, borderRadius: 12, padding: 12, borderWidth: 1, borderColor: c.border, gap: 6 },
  title: { fontFamily: fonts.textSemi, fontSize: 16, color: c.onSurface },
  meta: { fontFamily: fonts.text, fontSize: 13, color: c.onSurfaceTertiary },
  doc: { flexDirection: "row", gap: 8, alignItems: "center", padding: 10, borderRadius: 8, borderWidth: 1, borderColor: c.border, minHeight: 44 },
  docText: { flex: 1, fontFamily: fonts.textMedium, fontSize: 13, color: c.onSurface },
  actions: { flexDirection: "row", gap: 8, marginTop: 4 },
  input: { minHeight: 90, borderRadius: 12, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, padding: 12, fontFamily: fonts.text, fontSize: 15, color: c.onSurface, textAlignVertical: "top" },
  err: { color: c.error, fontFamily: fonts.textMedium },
}));
