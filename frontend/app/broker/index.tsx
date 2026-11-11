import React from "react";
import { Redirect, useRouter } from "expo-router";
import { ActivityIndicator, RefreshControl, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAuth } from "@/src/auth";
import { Badge, Button, EmptyState, ScreenHeader } from "@/src/components/ui";
import { useBrokerDashboard } from "@/src/lister";
import { useFocusedRefresh } from "@/src/useFocusedRefresh";
import { fonts, makeStyles } from "@/src/theme";

export default function BrokerDashboard() {
  const { user, loading } = useAuth();
  const q = useBrokerDashboard();
  useFocusedRefresh(q.refetch, !!user);
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  if (loading) return <ActivityIndicator />;
  if (!user) return <Redirect href="/login" />;
  const application = q.data?.application;
  const listings = q.data?.listings ?? {};
  const leads = q.data?.leads ?? {};
  return <View style={styles.screen}>
    <ScreenHeader title="Broker dashboard" topInset={insets.top} onBack={() => router.canGoBack() ? router.back() : router.replace("/profile")} />
    {q.isLoading ? <ActivityIndicator /> : q.isError ? <EmptyState icon="cloud-offline-outline" title={q.error.message} cta="Retry" onPress={() => q.refetch()} /> :
      <ScrollView contentContainerStyle={{ padding: 16, gap: 16, paddingBottom: insets.bottom + 24 }} refreshControl={<RefreshControl refreshing={q.isRefetching} onRefresh={() => { void q.refetch(); }} />}>
        <View style={styles.card}>
          <Text style={styles.title}>{application?.firm_name || application?.full_name || "Become a LANDVILLA broker"}</Text>
          <Badge label={application?.status.toUpperCase() ?? "NOT APPLIED"} kind={application?.status === "approved" ? "verified" : "muted"} />
          <Text style={styles.text}>{application?.status === "approved" ? "You can submit broker listings for moderation." : application?.status === "pending" ? "Your application is under review. Pull down to check for a decision." : application?.status === "suspended" ? "Broker posting is suspended. An administrator must review your account." : "Apply with your business details and private verification documents."}</Text>
          {!!application?.admin_note && <Text style={styles.text}>Reviewer note: {application.admin_note}</Text>}
          {(!application || application.status === "rejected") && <Button label={application ? "Revise and resubmit" : "Apply for verification"} onPress={() => router.push("/broker/apply")} />}
        </View>
        <View style={styles.card}>
          <Text style={styles.title}>Broker activity</Text>
          <Text style={styles.text}>Total listings: {Object.values(listings).reduce((a, b) => a + b, 0)}</Text>
          <Text style={styles.text}>Active: {listings.active ?? 0} · Pending approval: {listings.pending_review ?? 0}</Text>
          <Text style={styles.text}>Enquiries: {Object.values(leads).reduce((a, b) => a + b, 0)} · New leads: {leads.new ?? 0}</Text>
          {!Object.keys(listings).length && <Text style={styles.text}>No broker listings yet. Approved brokers can submit their first property below.</Text>}
        </View>
        {application?.status === "approved" && <Button label="Create broker listing" onPress={() => router.push("/post/form?as=broker")} />}
        <Button label="Manage listings" variant="outline" onPress={() => router.push("/listings")} />
        <Button label="Lead inbox" variant="outline" onPress={() => router.push("/leads")} />
      </ScrollView>}
  </View>;
}
const useStyles = makeStyles(c => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  card: { padding: 16, gap: 12, borderRadius: 12, backgroundColor: c.surface, borderWidth: 1, borderColor: c.border },
  title: { fontFamily: fonts.textSemi, fontSize: 18, color: c.onSurface },
  text: { fontFamily: fonts.text, fontSize: 14, lineHeight: 21, color: c.onSurfaceSecondary },
}));
