import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import React from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { SafetyActions } from "@/src/components/SafetyActions";
import { Thread } from "@/src/components/Thread";
import { Badge, EmptyState, ScreenHeader } from "@/src/components/ui";
import { formatPrice } from "@/src/data";
import { useLang } from "@/src/i18n";

import { fonts, makeStyles, useTheme } from "@/src/theme";

export default function BuyerEnquiry() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const { tx, pick, lang } = useLang();
  const router = useRouter();
  const key = ["enquiry", id];
  const qc = useQueryClient();
  const q = useQuery({ queryKey: key, queryFn: () => api<any>(`/enquiries/${id}`) });
  const e = q.data;
  const back = () => (router.canGoBack() ? router.back() : router.replace("/enquiries"));

  if (q.isLoading) return <View style={[styles.screen, { justifyContent: "center" }]}><ActivityIndicator color={colors.brandPrimary} /></View>;
  if (!e) return <View style={[styles.screen, { paddingTop: insets.top }]}><EmptyState icon="alert-circle-outline" title={tx("Enquiry not found", "पूछताछ नहीं मिली")} cta={tx("Back", "वापस")} onPress={back} testID="enquiry-error" /></View>;

  return (
    <View style={styles.screen}>
      <ScreenHeader title={tx("Your enquiry", "आपकी पूछताछ")} onBack={back} topInset={insets.top} />
      <KeyboardAwareScrollView bottomOffset={24} contentContainerStyle={{ padding: 16, gap: 16, paddingBottom: insets.bottom + 24 }} keyboardShouldPersistTaps="handled">
        {e.property && (
          <Pressable style={styles.card} onPress={() => router.push(`/property/${e.property.id}`)} testID="enquiry-property-link">
            <Text style={styles.title}>{pick(e.property, "title")}</Text>
            <Text style={styles.sub}>{formatPrice(e.property.price, e.property.purpose, lang)}</Text>
          </Pressable>
        )}
        <View style={styles.card}>
          <View style={{ flexDirection: "row", gap: 6 }}>
            <Badge label={e.status === "replied" ? tx("Replied", "जवाब मिला") : e.status === "closed" ? tx("Closed", "बंद") : tx("Sent", "भेजी गई")} kind={e.status === "replied" ? "verified" : "muted"} testID="enquiry-status" />
          </View>
          <Text style={styles.small} testID="enquiry-consent-state">
            {e.share_phone_consent
              ? tx("You shared your number (+91 " + e.phone + ") with the lister for this enquiry.", "आपने इस पूछताछ के लिए अपना नंबर (+91 " + e.phone + ") लिस्टर के साथ साझा किया है।")
              : tx("Your number is hidden from the lister. Chat here instead.", "आपका नंबर लिस्टर से छिपा है। यहाँ बात करें।")}
          </Text>
        </View>
        <View style={styles.card}>
          <Thread enquiryId={e.id} messages={e.messages ?? []} me="buyer" queryKey={key} blocked={e.messaging_blocked} />
        </View>
        <SafetyActions enquiryId={e.id} initialBlocked={e.blocked_by_me} onChanged={() => qc.invalidateQueries({ queryKey: key })} />
      </KeyboardAwareScrollView>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  card: { backgroundColor: c.surface, borderRadius: 12, padding: 16, borderWidth: 1, borderColor: c.border, gap: 8 },
  title: { fontFamily: fonts.textSemi, fontSize: 15, color: c.onSurface },
  sub: { fontFamily: fonts.textMedium, fontSize: 14, color: c.brandPrimary },
  small: { fontFamily: fonts.text, fontSize: 13, color: c.muted, lineHeight: 19 },
}));
