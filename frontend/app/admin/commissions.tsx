import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Sheet } from "@/src/components/Sheet";
import { useToast } from "@/src/components/Toast";
import { Badge, Button, Checkbox, Chip, EmptyState, ScreenHeader } from "@/src/components/ui";
import { fonts, makeStyles, useTheme } from "@/src/theme";

const NEW = { property_description: "", payer_type: "owner", payer_name: "", rate_percent: "1", calculation_method: "Percentage of final declared sale value",
  due_terms: "Within 15 days of registry", taxes_note: "GST as applicable, extra", cancellation_terms: "", dispute_process: "", service_description: "" };
const FIELDS: [keyof typeof NEW, string][] = [["property_description", "Property"], ["payer_name", "Payer name"], ["rate_percent", "Rate %"], ["service_description", "Service LANDVILLA provides"],
  ["calculation_method", "Calculation method"], ["due_terms", "Due date / terms"], ["taxes_note", "Taxes"], ["cancellation_terms", "Cancellation terms"], ["dispute_process", "Dispute process"]];
type Op = { kind: "status"; c: any; status: string } | { kind: "invoice"; c: any } | { kind: "payment"; c: any } | null;

export default function AdminCommissions() {
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const { user } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [f, setF] = useState<any>(NEW);
  const [op, setOp] = useState<Op>(null);
  const [v, setV] = useState<Record<string, string>>({});
  const [err, setErr] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const q = useQuery({ queryKey: ["admin-commissions"], queryFn: () => api<{ items: any[]; settings: any }>("/admin/commissions"), enabled: user?.role === "admin" });
  const done = (msg: string) => { qc.invalidateQueries({ queryKey: ["admin-commissions"] }); setOp(null); setCreating(false); toast.show(msg, "success"); };
  const m = useMutation({ mutationFn: (p: { path: string; method?: string; body: any }) => api(p.path, { method: p.method ?? "POST", body: p.body }), onSuccess: () => done("Saved"), onError: (e: any) => setErr(e.message) });
  const s = q.data?.settings;

  if (user?.role !== "admin") return <View style={[styles.screen, { paddingTop: insets.top + 40 }]}><EmptyState icon="lock-closed-outline" title="Admin access required" cta="Go back" onPress={() => router.back()} testID="admin-denied" /></View>;

  const submitOp = () => {
    setErr("");
    if (!op) return;
    if (op.kind === "status") m.mutate({ path: `/admin/commissions/${op.c.id}/status`, body: { status: op.status, note: v.note ?? "", acceptance_evidence: v.evidence, deal_value: v.deal ? Number(v.deal) : undefined, deal_report_source: v.source } });
    if (op.kind === "invoice") m.mutate({ path: `/admin/commissions/${op.c.id}/invoices`, body: { invoice_number: v.number ?? "", amount: Number(v.amount || 0), tax_amount: Number(v.tax || 0) } });
    if (op.kind === "payment") m.mutate({ path: `/admin/commissions/${op.c.id}/payments`, body: { amount: Number(v.amount || 0), method: v.method ?? "", reference: v.reference ?? "" } });
  };
  const inp = (k: string, ph: string, numeric = false) => (
    <TextInput key={k} testID={`op-${k}`} value={v[k] ?? ""} onChangeText={(x) => setV({ ...v, [k]: x })} placeholder={ph} placeholderTextColor={colors.muted} keyboardType={numeric ? "decimal-pad" : "default"} style={styles.input} />
  );

  return (
    <View style={styles.screen}>
      <ScreenHeader title="Commission agreements" onBack={() => router.back()} topInset={insets.top} />
      {q.isLoading ? <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 40 }} /> : (
        <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: insets.bottom + 24 }}>
          <View style={styles.banner} testID="commission-settings">
            <Text style={styles.bannerText}>Default rate {s?.default_rate_percent}% · Auto-charge: never · Written agreement required</Text>
            <Text style={styles.bannerText}>Legal review: {s?.legal_review_complete ? "complete" : "PENDING"} · Collection: {s?.collection_enabled ? "enabled" : "DISABLED"}</Text>
          </View>
          <Button label="New agreement" icon="add" onPress={() => { setErr(""); setF(NEW); setCreating(true); }} testID="commission-new-btn" />
          {q.data?.items.length === 0 && <EmptyState icon="document-outline" title="No commission records" testID="commissions-empty" />}
          {q.data?.items.map((c) => (
            <View key={c.id} style={styles.card} testID={`commission-${c.id}`}>
              <Pressable onPress={() => setOpen(open === c.id ? null : c.id)}>
                <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
                  <Text style={styles.title} numberOfLines={1}>{c.property_description}</Text>
                  <Badge label={c.status.replace("_", " ").toUpperCase()} kind={c.status === "paid" ? "verified" : c.status === "disputed" ? "demo" : "muted"} testID={`commission-status-${c.id}`} />
                </View>
                <Text style={styles.meta}>{c.payer_type}: {c.payer_name} · {c.rate_percent}%{c.deal_value ? ` of ₹${c.deal_value.toLocaleString("en-IN")}` : ""}</Text>
                <Text style={styles.meta}>Commission: {c.commission_amount != null ? `₹${c.commission_amount.toLocaleString("en-IN")}` : "not payable (needs accepted agreement + deal value)"}</Text>
              </Pressable>
              {open === c.id && (
                <View style={{ gap: 4 }}>
                  {c.acceptance_evidence && <Text style={styles.meta}>Acceptance: {c.acceptance_evidence}</Text>}
                  {c.invoices.map((i: any) => <Text key={i.id} style={styles.meta}>Invoice {i.invoice_number}: ₹{i.amount} + tax ₹{i.tax_amount}</Text>)}
                  {c.payments.map((p: any) => <Text key={p.id} style={styles.meta}>Payment ₹{p.amount} · {p.method} · {p.reference}</Text>)}
                  <Text style={[styles.meta, { fontFamily: fonts.textSemi }]}>Audit trail</Text>
                  {c.audit.map((a: any, i: number) => <Text key={i} style={styles.meta}>{new Date(a.at).toLocaleString("en-IN")} · {a.action}{a.details?.note ? ` – ${a.details.note}` : ""}</Text>)}
                </View>
              )}
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
                {c.allowed_next.map((st: string) => <Chip key={st} label={st.replace("_", " ")} onPress={() => { setErr(""); setV({}); setOp({ kind: "status", c, status: st }); }} testID={`commission-to-${st}-${c.id}`} />)}
                {["approved_payable", "invoiced"].includes(c.status) && <Chip label="Add invoice" icon="receipt-outline" onPress={() => { setErr(""); setV({}); setOp({ kind: "invoice", c }); }} testID={`commission-invoice-${c.id}`} />}
                {c.status === "invoiced" && <Chip label="Record payment" icon="cash-outline" onPress={() => { setErr(""); setV({}); setOp({ kind: "payment", c }); }} testID={`commission-payment-${c.id}`} />}
              </View>
            </View>
          ))}
        </ScrollView>
      )}
      <Sheet visible={creating} onClose={() => setCreating(false)} title="New commission agreement" testID="commission-create-sheet"
        footer={<Button label="Create draft" loading={m.isPending} testID="commission-create-btn" onPress={() => { setErr(""); m.mutate({ path: "/admin/commissions", body: { ...f, rate_percent: Number(f.rate_percent) } }); }} />}>
        <KeyboardAwareScrollView bottomOffset={24} contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 16, gap: 8 }} keyboardShouldPersistTaps="handled">
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            {["owner", "buyer", "tenant", "other"].map((p) => <Chip key={p} label={`Payer: ${p}`} selected={f.payer_type === p} onPress={() => setF({ ...f, payer_type: p })} testID={`commission-payer-${p}`} />)}
          </View>
          {FIELDS.map(([k, label]) => (
            <TextInput key={k} testID={`commission-field-${k}`} value={f[k]} onChangeText={(x) => setF({ ...f, [k]: x })} placeholder={label} placeholderTextColor={colors.muted} style={styles.input} keyboardType={k === "rate_percent" ? "decimal-pad" : "default"} />
          ))}
          {!!err && <Text style={{ color: colors.error }} testID="commission-create-error">{err}</Text>}
        </KeyboardAwareScrollView>
      </Sheet>
      <Sheet visible={!!op} onClose={() => setOp(null)} title={op?.kind === "status" ? `Move to: ${op.status.replace("_", " ")}` : op?.kind === "invoice" ? "Add invoice" : "Record payment"} testID="commission-op-sheet"
        footer={<Button label="Confirm" loading={m.isPending} onPress={submitOp} testID="commission-op-confirm-btn" />}>
        <View style={{ paddingHorizontal: 16, paddingBottom: 16, gap: 8 }}>
          {op?.kind === "status" && op.status === "agreement_accepted" && inp("evidence", "Acceptance evidence (signed copy ref, e-sign ID, date)")}
          {op?.kind === "status" && op.status === "deal_reported" && <>{inp("deal", "Declared deal value (₹)", true)}{inp("source", "Reported by / source")}</>}
          {op?.kind === "status" && inp("note", "Note for audit trail (required)")}
          {op?.kind === "invoice" && <>{inp("number", "Invoice number")}{inp("amount", "Amount (₹)", true)}{inp("tax", "Tax (₹)", true)}</>}
          {op?.kind === "payment" && <>{inp("amount", "Amount (₹)", true)}{inp("method", "Method (NEFT, UPI…)")}{inp("reference", "Reference / UTR")}</>}
          {!!err && <Text style={{ color: colors.error }} testID="commission-op-error">{err}</Text>}
        </View>
      </Sheet>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  banner: { padding: 12, borderRadius: 12, backgroundColor: c.brandTertiary, gap: 4 },
  bannerText: { fontFamily: fonts.textMedium, fontSize: 13, color: c.onBrandTertiary },
  card: { backgroundColor: c.surface, borderRadius: 12, padding: 12, borderWidth: 1, borderColor: c.border, gap: 8 },
  title: { flex: 1, fontFamily: fonts.textSemi, fontSize: 15, color: c.onSurface },
  meta: { fontFamily: fonts.text, fontSize: 13, color: c.onSurfaceTertiary },
  input: { minHeight: 46, borderRadius: 12, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, paddingHorizontal: 12, fontFamily: fonts.text, fontSize: 15, color: c.onSurface },
}));
