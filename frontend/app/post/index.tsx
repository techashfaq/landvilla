import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useRouter } from "expo-router";
import React from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAuth } from "@/src/auth";
import { Badge, Button, EmptyState, ScreenHeader } from "@/src/components/ui";
import { useLang } from "@/src/i18n";
import { useLister } from "@/src/lister";
import { fonts, makeStyles, useTheme } from "@/src/theme";

export default function PostStart() {
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const { tx } = useLang();
  const { user } = useAuth();
  const router = useRouter();
  const q = useLister();
  const broker = q.data?.broker;
  const back = () => (router.canGoBack() ? router.back() : router.replace("/profile"));

  if (!user) {
    return (
      <View style={styles.screen}>
        <ScreenHeader title={tx("Post a property", "प्रॉपर्टी पोस्ट करें")} onBack={back} topInset={insets.top} />
        <EmptyState icon="person-circle-outline" title={tx("Please sign in to post a property", "प्रॉपर्टी पोस्ट करने के लिए साइन इन करें")} cta={tx("Sign in", "साइन इन")} onPress={() => router.push("/login")} testID="post-login" />
      </View>
    );
  }

  const brokerStatus = broker?.status;
  const brokerText = {
    pending: tx("Your broker verification is under review. You can post as Owner meanwhile.", "आपका ब्रोकर सत्यापन समीक्षा में है। तब तक आप मालिक के रूप में पोस्ट कर सकते हैं।"),
    rejected: tx("Your broker request was not approved. You can apply again.", "आपका ब्रोकर अनुरोध स्वीकृत नहीं हुआ। आप फिर से आवेदन कर सकते हैं।"),
    suspended: tx("Your broker account is suspended. Contact support.", "आपका ब्रोकर खाता निलंबित है। सहायता से संपर्क करें।"),
    approved: tx("Verified broker – you can post listings as a broker.", "सत्यापित ब्रोकर – आप ब्रोकर के रूप में पोस्ट कर सकते हैं।"),
  };

  return (
    <View style={styles.screen}>
      <ScreenHeader title={tx("Post a property", "प्रॉपर्टी पोस्ट करें")} onBack={back} topInset={insets.top} />
      {q.isLoading ? (
        <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 40 }} />
      ) : (
        <ScrollView contentContainerStyle={{ padding: 16, gap: 16, paddingBottom: insets.bottom + 24 }}>
          <Text style={styles.lead}>{tx("How are you posting this property?", "आप यह प्रॉपर्टी किस रूप में पोस्ट कर रहे हैं?")}</Text>

          <Pressable testID="post-as-owner-btn" style={styles.card} onPress={() => router.push("/post/form?as=owner")}>
            <View style={styles.iconWrap}><Ionicons name="home-outline" size={26} color={colors.brandPrimary} /></View>
            <View style={{ flex: 1 }}>
              <Text style={styles.cardTitle}>{tx("I'm the Owner", "मैं मालिक हूँ")}</Text>
              <Text style={styles.cardSub}>{tx("Post your own property. Every listing is reviewed by our team before it goes live.", "अपनी प्रॉपर्टी पोस्ट करें। हर लिस्टिंग लाइव होने से पहले हमारी टीम जाँचती है।")}</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.muted} />
          </Pressable>

          <Pressable
            testID="post-as-broker-btn"
            style={[styles.card, brokerStatus === "suspended" && { opacity: 0.6 }]}
            disabled={brokerStatus === "suspended"}
            onPress={() => (q.data?.can_post_as_broker ? router.push("/post/form?as=broker") : brokerStatus === "pending" ? null : router.push("/broker/apply"))}
          >
            <View style={styles.iconWrap}><Ionicons name="briefcase-outline" size={26} color={colors.brandPrimary} /></View>
            <View style={{ flex: 1, gap: 4 }}>
              <Text style={styles.cardTitle}>{tx("I'm a Broker", "मैं ब्रोकर हूँ")}</Text>
              <Text style={styles.cardSub}>
                {brokerStatus ? brokerText[brokerStatus] : tx("Broker posting needs identity verification and admin approval first.", "ब्रोकर पोस्टिंग के लिए पहले पहचान सत्यापन और एडमिन स्वीकृति ज़रूरी है।")}
              </Text>
              {brokerStatus && (
                <View style={{ flexDirection: "row" }}>
                  <Badge testID="broker-status-badge" label={brokerStatus.toUpperCase()} kind={brokerStatus === "approved" ? "verified" : brokerStatus === "pending" ? "muted" : "demo"} />
                </View>
              )}
              {broker?.admin_note && brokerStatus !== "approved" && <Text style={styles.note}>{tx("Note", "नोट")}: {broker.admin_note}</Text>}
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.muted} />
          </Pressable>

          <Button label={tx("My listings", "मेरी लिस्टिंग")} variant="outline" icon="list-outline" onPress={() => router.push("/listings")} testID="go-my-listings-btn" />
        </ScrollView>
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  lead: { fontFamily: fonts.displaySemi, fontSize: 18, color: c.onSurface },
  card: { flexDirection: "row", gap: 12, alignItems: "center", padding: 16, borderRadius: 12, backgroundColor: c.surface, borderWidth: 1, borderColor: c.border },
  iconWrap: { width: 52, height: 52, borderRadius: 26, backgroundColor: c.brandTertiary, alignItems: "center", justifyContent: "center" },
  cardTitle: { fontFamily: fonts.textSemi, fontSize: 16, color: c.onSurface },
  cardSub: { fontFamily: fonts.text, fontSize: 13, color: c.muted, lineHeight: 19 },
  note: { fontFamily: fonts.textMedium, fontSize: 13, color: c.error },
}));
