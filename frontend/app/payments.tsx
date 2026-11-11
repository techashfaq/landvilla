import React from "react";
import { ActivityIndicator, FlatList, Text, View } from "react-native";
import { Redirect, useRouter } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useFocusedRefresh } from "@/src/useFocusedRefresh";
import { useToast } from "@/src/components/Toast";
import { PlayBillingPanel } from "@/src/components/PlayBillingPanel";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Button, EmptyState, ScreenHeader } from "@/src/components/ui";
import { fonts, makeStyles } from "@/src/theme";

type Payment = { id: string; status: string; amount: number | null; provider?: string; plan_slug: string; created_at: string; razorpay_payment_id?: string; refund_status?: string; featured_from?: string; featured_until?: string };
export default function Payments() {
  const styles = useStyles(); const router = useRouter(); const insets = useSafeAreaInsets(); const { user, loading } = useAuth();
  const query = useQuery({ queryKey: ["payments", user?.user_id], queryFn: () => api<{ items: Payment[] }>("/payments/mine"), enabled: !!user });
  useFocusedRefresh(query.refetch, !!user);
  const qc = useQueryClient(); const toast = useToast();
  const refresh = useMutation({ mutationFn: (id: string) => api(`/payments/${id}/refresh`, { method: "POST", body: {} }), onSuccess: () => { qc.invalidateQueries({ queryKey: ["payments"] }); qc.invalidateQueries({ queryKey: ["my-listings"] }); qc.invalidateQueries({ queryKey: ["properties"] }); }, onError: (e: Error) => toast.show(e.message, "error") });
  if (loading) return <ActivityIndicator />;
  if (!user) return <Redirect href="/login" />;
  return <View style={styles.screen}><ScreenHeader title="Payment history" topInset={insets.top} onBack={() => router.back()} />
    <PlayBillingPanel />
    {query.isPending ? <ActivityIndicator /> : query.isError ? <EmptyState icon="cloud-offline-outline" title={query.error.message} cta="Retry" onPress={() => query.refetch()} /> :
      <FlatList data={query.data.items} keyExtractor={p => p.id} contentContainerStyle={{ padding: 16, gap: 12 }} refreshing={query.isRefetching} onRefresh={() => query.refetch()}
        ListEmptyComponent={<EmptyState icon="receipt-outline" title="No payment records" />}
        renderItem={({ item }) => <View style={styles.card}><Text style={styles.title}>{item.amount === null ? "Google Play purchase" : `₹${(item.amount / 100).toLocaleString("en-IN")}`} · {item.status}</Text>
          <Text style={styles.text}>{item.plan_slug}</Text><Text selectable style={styles.text}>Reference: {item.id}</Text>
          {!!item.razorpay_payment_id && <Text selectable style={styles.text}>Payment: {item.razorpay_payment_id}</Text>}
          {!!item.refund_status && <Text style={styles.text}>Refund: {item.refund_status.replace(/_/g, " ")}</Text>}
          {!!item.featured_until && <Text style={styles.text}>Featured through {new Date(item.featured_until).toLocaleString("en-IN")}</Text>}
          {item.provider !== "google_play" && !["paid", "refunded"].includes(item.status) && <Button label="Check payment with provider" variant="outline" disabled={refresh.isPending} loading={refresh.isPending && refresh.variables === item.id} onPress={() => refresh.mutate(item.id)} />}
          <Text style={styles.text}>{new Date(item.created_at).toLocaleString("en-IN")}</Text></View>} />}
  </View>;
}
const useStyles = makeStyles(c => ({ screen: { flex: 1, backgroundColor: c.surface }, card: { padding: 16, borderWidth: 1, borderColor: c.border, borderRadius: 12, gap: 6 }, title: { color: c.onSurface, fontFamily: fonts.display, fontSize: 18 }, text: { color: c.onSurface, fontFamily: fonts.text } }));
