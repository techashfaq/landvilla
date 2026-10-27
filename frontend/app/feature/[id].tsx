import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { FEATURED_PURCHASE_ALLOWED } from "@/src/lister";
import { RazorpayCheckout, RzpOrder, RzpSuccess } from "@/src/components/RazorpayCheckout";
import { useToast } from "@/src/components/Toast";
import { Badge, Button, ScreenHeader } from "@/src/components/ui";
import { useLang } from "@/src/i18n";
import { fonts, makeStyles, useTheme } from "@/src/theme";

type Plan = { id: string; name_en: string; name_hi: string; price_inr: number; duration_days: number };

export default function FeatureListing() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const { tx, pick, lang } = useLang();
  const router = useRouter();
  const toast = useToast();
  const qc = useQueryClient();
  const plans = useQuery({ queryKey: ["featured-plans"], queryFn: () => api<{ items: Plan[]; payments_configured: boolean; mode: string | null }>("/featured-plans") });
  const [planId, setPlanId] = useState<string | null>(null);
  const [order, setOrder] = useState<RzpOrder | null>(null);
  const [result, setResult] = useState<{ kind: "success" | "failed" | "pending" | "cancelled"; text: string } | null>(null);

  const create = useMutation({
    mutationFn: () => api<RzpOrder>("/payments/featured/order", { method: "POST", body: { property_id: id, plan_id: planId } }),
    onSuccess: (o) => { setResult(null); setOrder(o); },
    onError: (e: any) => toast.show(e.message, "error"),
  });
  const verify = useMutation({
    mutationFn: (r: RzpSuccess) => api<any>("/payments/featured/verify", { method: "POST", body: r }),
    onSuccess: (o) => {
      qc.invalidateQueries({ queryKey: ["my-listings"] });
      qc.invalidateQueries({ queryKey: ["properties"] });
      if (o.status === "paid") {
        const until = new Date(o.featured_until).toLocaleDateString(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short", year: "numeric" });
        setResult({ kind: "success", text: tx(`Payment verified. Your listing is featured until ${until}.`, `भुगतान सत्यापित। आपकी लिस्टिंग ${until} तक फ़ीचर्ड है।`) });
      } else setResult({ kind: "pending", text: tx("Payment is pending. Featuring starts automatically once Razorpay confirms it.", "भुगतान लंबित है। Razorpay की पुष्टि के बाद फ़ीचर अपने आप शुरू होगा।") });
    },
    onError: (e: any) => setResult({ kind: "failed", text: e.message }),
  });
  const markFailed = (reason: "cancelled" | "failed", description = "") => {
    if (order) api("/payments/featured/failed", { method: "POST", body: { razorpay_order_id: order.razorpay_order_id, reason, description } }).catch(() => {});
  };

  const selected = plans.data?.items.find((p) => p.id === planId);

  return (
    <View style={styles.screen}>
      <ScreenHeader title={tx("Feature your listing", "लिस्टिंग फ़ीचर करें")} onBack={() => router.back()} topInset={insets.top} />
      {plans.isLoading ? (
        <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 40 }} />
      ) : (
        <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: insets.bottom + 24 }}>
          <Text style={styles.intro}>{tx("Featured listings appear at the top of search results in their area, with a Featured badge.", "फ़ीचर्ड लिस्टिंग अपने इलाके के खोज परिणामों में सबसे ऊपर, फ़ीचर्ड बैज के साथ दिखती हैं।")}</Text>
          {plans.data?.mode === "test" && (
            <View style={styles.testBanner} testID="test-mode-banner">
              <Ionicons name="flask-outline" size={18} color={colors.warning} />
              <Text style={styles.testText}>{tx("TEST MODE – no real money is charged. Use Razorpay test cards/UPI.", "टेस्ट मोड – कोई असली पैसा नहीं कटेगा। Razorpay टेस्ट कार्ड/UPI का उपयोग करें।")}</Text>
            </View>
          )}
          {plans.data?.items.map((p) => (
            <Pressable key={p.id} testID={`plan-${p.id}`} onPress={() => setPlanId(p.id)} style={[styles.plan, planId === p.id && styles.planOn]}>
              <Ionicons name={planId === p.id ? "radio-button-on" : "radio-button-off"} size={22} color={colors.brandPrimary} />
              <View style={{ flex: 1 }}>
                <Text style={styles.planName}>{pick(p, "name")}</Text>
                <Text style={styles.planSub}>{p.duration_days} {tx("days at the top of your area", "दिन अपने इलाके में सबसे ऊपर")}</Text>
              </View>
              <Text style={styles.planPrice}>₹{p.price_inr}</Text>
            </Pressable>
          ))}
          {result && (
            <View style={[styles.result, { borderColor: result.kind === "success" ? colors.success : result.kind === "pending" ? colors.warning : colors.error }]} testID={`payment-result-${result.kind}`}>
              <Badge label={result.kind.toUpperCase()} kind={result.kind === "success" ? "verified" : "demo"} />
              <Text style={styles.resultText}>{result.text}</Text>
            </View>
          )}
          {!FEATURED_PURCHASE_ALLOWED ? (
            <Text style={styles.err} testID="featured-not-available-in-app">{tx("Featured purchases are not available in the mobile app yet.", "फ़ीचर्ड खरीदारी अभी मोबाइल ऐप में उपलब्ध नहीं है।")}</Text>
          ) : !plans.data?.payments_configured ? (
            <Text style={styles.err} testID="payments-not-configured">{tx("Payments are not configured yet. Please try later.", "भुगतान अभी कॉन्फ़िगर नहीं है। कृपया बाद में प्रयास करें।")}</Text>
          ) : result?.kind === "success" ? (
            <Button label={tx("Back to my listings", "मेरी लिस्टिंग पर जाएं")} onPress={() => router.replace("/listings")} testID="payment-done-btn" />
          ) : (
            <Button
              label={selected ? tx(`Pay ₹${selected.price_inr}`, `₹${selected.price_inr} भुगतान करें`) : tx("Choose a plan", "प्लान चुनें")}
              disabled={!selected}
              loading={create.isPending || verify.isPending}
              onPress={() => create.mutate()}
              icon="lock-closed-outline"
              testID="pay-btn"
            />
          )}
          <Text style={styles.small}>{tx("Payments are processed securely by Razorpay. Featuring starts only after the payment is verified.", "भुगतान Razorpay द्वारा सुरक्षित रूप से होता है। भुगतान सत्यापन के बाद ही फ़ीचर शुरू होगा।")}</Text>
        </ScrollView>
      )}
      <RazorpayCheckout
        order={order}
        onSuccess={(r) => { setOrder(null); verify.mutate(r); }}
        onDismiss={() => { markFailed("cancelled"); setOrder(null); setResult({ kind: "cancelled", text: tx("Payment cancelled. You were not charged.", "भुगतान रद्द हुआ। कोई राशि नहीं कटी।") }); }}
        onFailed={(d) => { markFailed("failed", d); setOrder(null); setResult({ kind: "failed", text: d }); }}
      />
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  intro: { fontFamily: fonts.text, fontSize: 14, color: c.onSurfaceTertiary, lineHeight: 20 },
  testBanner: { flexDirection: "row", gap: 8, padding: 12, borderRadius: 12, backgroundColor: c.brandTertiary, alignItems: "center" },
  testText: { flex: 1, fontFamily: fonts.textMedium, fontSize: 13, color: c.onBrandTertiary },
  plan: { flexDirection: "row", alignItems: "center", gap: 12, padding: 16, borderRadius: 12, backgroundColor: c.surface, borderWidth: 1.5, borderColor: c.border },
  planOn: { borderColor: c.brandPrimary, backgroundColor: c.brandTertiary },
  planName: { fontFamily: fonts.textSemi, fontSize: 16, color: c.onSurface },
  planSub: { fontFamily: fonts.text, fontSize: 13, color: c.muted },
  planPrice: { fontFamily: fonts.display, fontSize: 22, color: c.brandPrimary },
  result: { padding: 12, borderRadius: 12, borderWidth: 1.5, gap: 8, backgroundColor: c.surface, alignItems: "flex-start" },
  resultText: { fontFamily: fonts.textMedium, fontSize: 14, color: c.onSurface, lineHeight: 20 },
  err: { fontFamily: fonts.textMedium, fontSize: 14, color: c.error },
  small: { fontFamily: fonts.text, fontSize: 12, color: c.muted, lineHeight: 17 },
}));
