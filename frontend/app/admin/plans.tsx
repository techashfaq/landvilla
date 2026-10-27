import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { ActivityIndicator, Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { useToast } from "@/src/components/Toast";
import { Badge, Button, Checkbox, EmptyState, ScreenHeader } from "@/src/components/ui";
import { fonts, makeStyles, useTheme } from "@/src/theme";

type Plan = { id: string; name_en: string; name_hi: string; price_inr: number; duration_days: number; is_active: boolean };

function PlanEditor({ plan }: { plan: Plan }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const toast = useToast();
  const qc = useQueryClient();
  const [price, setPrice] = useState(String(plan.price_inr));
  const [days, setDays] = useState(String(plan.duration_days));
  const [active, setActive] = useState(plan.is_active);
  const m = useMutation({
    mutationFn: () => api(`/admin/featured-plans/${plan.id}`, { method: "PUT", body: {
      name_en: `Featured · ${days} days`, name_hi: `फ़ीचर्ड · ${days} दिन`, price_inr: parseInt(price, 10), duration_days: parseInt(days, 10), is_active: active } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-plans"] }); qc.invalidateQueries({ queryKey: ["featured-plans"] }); toast.show("Plan saved", "success"); },
    onError: (e: any) => toast.show(e.message, "error"),
  });
  return (
    <View style={styles.card} testID={`plan-editor-${plan.id}`}>
      <Text style={styles.title}>{plan.name_en}</Text>
      <View style={{ flexDirection: "row", gap: 12 }}>
        <View style={{ flex: 1 }}>
          <Text style={styles.label}>Price (₹)</Text>
          <TextInput testID={`plan-price-${plan.id}`} value={price} onChangeText={(v) => setPrice(v.replace(/\D/g, ""))} keyboardType="number-pad" style={styles.input} placeholderTextColor={colors.muted} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.label}>Days</Text>
          <TextInput testID={`plan-days-${plan.id}`} value={days} onChangeText={(v) => setDays(v.replace(/\D/g, ""))} keyboardType="number-pad" style={styles.input} placeholderTextColor={colors.muted} />
        </View>
      </View>
      <Checkbox checked={active} onToggle={() => setActive(!active)} label="Plan enabled for listers" testID={`plan-active-${plan.id}`} />
      <Button label="Save plan" onPress={() => m.mutate()} loading={m.isPending} disabled={!price || !days} testID={`plan-save-${plan.id}`} />
    </View>
  );
}

export default function AdminPlans() {
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const { user } = useAuth();
  const plans = useQuery({ queryKey: ["admin-plans"], queryFn: () => api<{ items: Plan[] }>("/admin/featured-plans"), enabled: user?.role === "admin" });
  const pays = useQuery({ queryKey: ["admin-payments"], queryFn: () => api<{ items: any[] }>("/admin/payments"), enabled: user?.role === "admin" });

  if (user?.role !== "admin") return <View style={[styles.screen, { paddingTop: insets.top + 40 }]}><EmptyState icon="lock-closed-outline" title="Admin access required" cta="Go back" onPress={() => router.back()} testID="admin-denied" /></View>;

  return (
    <View style={styles.screen}>
      <ScreenHeader title="Featured plans & payments" onBack={() => router.back()} topInset={insets.top} />
      <KeyboardAwareScrollView bottomOffset={24} contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: insets.bottom + 24 }} keyboardShouldPersistTaps="handled">
        {plans.isLoading ? <ActivityIndicator color={colors.brandPrimary} /> : plans.data?.items.map((p) => <PlanEditor key={`${p.id}-${p.price_inr}-${p.duration_days}-${p.is_active}`} plan={p} />)}
        <Text style={styles.section}>Recent payments</Text>
        {pays.data?.items.length === 0 && <Text style={styles.meta}>No payments yet.</Text>}
        {pays.data?.items.map((o) => (
          <View key={o.id} style={styles.payRow} testID={`payment-row-${o.id}`}>
            <View style={{ flex: 1 }}>
              <Text style={styles.payTitle}>₹{o.amount / 100} · {o.plan_slug}</Text>
              <Text style={styles.meta}>{o.property_id} · {new Date(o.created_at).toLocaleString("en-IN")}</Text>
            </View>
            <View style={{ gap: 4, alignItems: "flex-end" }}>
              <Badge label={o.status.toUpperCase()} kind={o.status === "paid" ? "verified" : "muted"} />
              <Badge label={o.mode.toUpperCase()} kind="demo" />
            </View>
          </View>
        ))}
      </KeyboardAwareScrollView>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  card: { backgroundColor: c.surface, borderRadius: 12, padding: 16, borderWidth: 1, borderColor: c.border, gap: 8 },
  title: { fontFamily: fonts.textSemi, fontSize: 16, color: c.onSurface },
  label: { fontFamily: fonts.textSemi, fontSize: 13, color: c.onSurfaceSecondary, marginBottom: 6 },
  input: { height: 48, borderRadius: 12, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, paddingHorizontal: 12, fontFamily: fonts.text, fontSize: 16, color: c.onSurface },
  section: { fontFamily: fonts.displaySemi, fontSize: 18, color: c.onSurface, marginTop: 12 },
  meta: { fontFamily: fonts.text, fontSize: 12, color: c.muted },
  payRow: { flexDirection: "row", gap: 8, padding: 12, borderRadius: 12, backgroundColor: c.surface, borderWidth: 1, borderColor: c.border },
  payTitle: { fontFamily: fonts.textSemi, fontSize: 14, color: c.onSurface },
}));
