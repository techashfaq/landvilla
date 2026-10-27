import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useState } from "react";
import { ActivityIndicator, Linking, Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { Thread } from "@/src/components/Thread";
import { useToast } from "@/src/components/Toast";
import { Button, Chip, EmptyState, ScreenHeader } from "@/src/components/ui";
import { formatPrice } from "@/src/data";
import { useLang } from "@/src/i18n";
import { LEAD_STATUS } from "@/src/lister";
import { fonts, makeStyles, useTheme } from "@/src/theme";

export default function LeadDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const { tx, pick, lang } = useLang();
  const router = useRouter();
  const toast = useToast();
  const qc = useQueryClient();
  const [note, setNote] = useState("");
  const key = ["lead", id];
  const q = useQuery({ queryKey: key, queryFn: () => api<any>(`/leads/${id}`) });
  const upd = useMutation({
    mutationFn: (body: any) => api(`/leads/${id}`, { method: "PATCH", body }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: key }); qc.invalidateQueries({ queryKey: ["leads"] }); toast.show(tx("Lead updated", "लीड अपडेट हुई"), "success"); },
    onError: (e: any) => toast.show(e.message, "error"),
  });
  const l = q.data;
  const back = () => (router.canGoBack() ? router.back() : router.replace("/leads"));

  if (q.isLoading) return <View style={[styles.screen, { justifyContent: "center" }]}><ActivityIndicator color={colors.brandPrimary} /></View>;
  if (!l) return <View style={[styles.screen, { paddingTop: insets.top }]}><EmptyState icon="alert-circle-outline" title={tx("Lead not found", "लीड नहीं मिली")} cta={tx("Back", "वापस")} onPress={back} testID="lead-error" /></View>;

  const followIn = (days: number) => {
    const d = new Date();
    d.setDate(d.getDate() + days);
    d.setHours(10, 0, 0, 0);
    upd.mutate({ follow_up_at: d.toISOString() });
  };

  return (
    <View style={styles.screen}>
      <ScreenHeader title={l.name} onBack={back} topInset={insets.top} />
      <KeyboardAwareScrollView bottomOffset={24} contentContainerStyle={{ padding: 16, gap: 16, paddingBottom: insets.bottom + 24 }} keyboardShouldPersistTaps="handled">
        {l.property && (
          <View style={styles.card}>
            <Text style={styles.propTitle}>{pick(l.property, "title")}</Text>
            <Text style={styles.propSub}>{formatPrice(l.property.price, l.property.purpose, lang)}</Text>
          </View>
        )}
        <View style={styles.card} testID="lead-contact-card">
          <Text style={styles.label}>{tx("Contact", "संपर्क")}</Text>
          {l.share_phone_consent && l.phone ? (
            <>
              <Text style={styles.phone} testID="lead-phone-full">+91 {l.phone}</Text>
              <Text style={styles.small}>{tx("The buyer agreed to share this number for this enquiry. Access is logged.", "खरीदार ने इस पूछताछ के लिए नंबर साझा करने की सहमति दी है। एक्सेस दर्ज होता है।")}</Text>
              <Button label={tx("Call", "कॉल करें")} icon="call-outline" onPress={() => Linking.openURL(`tel:+91${l.phone}`)} testID="lead-call-btn" />
            </>
          ) : (
            <>
              <Text style={styles.phone} testID="lead-phone-masked">+91 {l.phone_masked}</Text>
              <View style={styles.privacyRow}>
                <Ionicons name="lock-closed-outline" size={16} color={colors.muted} />
                <Text style={styles.small}>{tx("The buyer hasn't shared their number. Reply using in-app messages below.", "खरीदार ने नंबर साझा नहीं किया है। नीचे ऐप संदेशों से जवाब दें।")}</Text>
              </View>
            </>
          )}
          {!!l.message && <Text style={styles.msg}>"{l.message}"</Text>}
          <Text style={styles.small}>{tx("Intent", "उद्देश्य")}: {l.intent.replace("_", " ")} · {new Date(l.created_at).toLocaleString(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.label}>{tx("Status", "स्थिति")}</Text>
          <View style={styles.row}>
            {Object.entries(LEAD_STATUS).map(([k, v]) => (
              <Chip key={k} label={tx(v.en, v.hi)} selected={l.status === k} onPress={() => upd.mutate({ status: k })} testID={`lead-set-${k}`} />
            ))}
          </View>
          <Text style={styles.label}>{tx("Follow-up reminder", "फ़ॉलो-अप रिमाइंडर")}</Text>
          {l.follow_up_at && <Text style={styles.small} testID="lead-followup-date">{tx("Scheduled", "निर्धारित")}: {new Date(l.follow_up_at).toLocaleDateString(lang === "hi" ? "hi-IN" : "en-IN", { weekday: "short", day: "numeric", month: "short" })}</Text>}
          <View style={styles.row}>
            <Chip label={tx("Tomorrow", "कल")} onPress={() => followIn(1)} testID="lead-follow-1" />
            <Chip label={tx("In 3 days", "3 दिन में")} onPress={() => followIn(3)} testID="lead-follow-3" />
            <Chip label={tx("Next week", "अगले सप्ताह")} onPress={() => followIn(7)} testID="lead-follow-7" />
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.label}>{tx("Private notes", "निजी नोट्स")}</Text>
          {(l.notes ?? []).map((n: any) => (
            <Text key={n.id} style={styles.note}>• {n.text} <Text style={styles.small}>({new Date(n.at).toLocaleDateString(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short" })})</Text></Text>
          ))}
          <TextInput testID="lead-note-input" value={note} onChangeText={setNote} placeholder={tx("e.g. Called, visit on Sunday", "जैसे कॉल किया, रविवार को विज़िट")} placeholderTextColor={colors.muted} style={styles.input} maxLength={1000} />
          <Button label={tx("Add note", "नोट जोड़ें")} variant="outline" disabled={!note.trim()} loading={upd.isPending} onPress={() => { upd.mutate({ note }); setNote(""); }} testID="lead-add-note-btn" />
        </View>

        <View style={styles.card}>
          <Thread enquiryId={l.id} messages={l.messages ?? []} me="lister" queryKey={key} />
        </View>
      </KeyboardAwareScrollView>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  card: { backgroundColor: c.surface, borderRadius: 12, padding: 16, borderWidth: 1, borderColor: c.border, gap: 10 },
  propTitle: { fontFamily: fonts.textSemi, fontSize: 15, color: c.onSurface },
  propSub: { fontFamily: fonts.textMedium, fontSize: 14, color: c.brandPrimary },
  label: { fontFamily: fonts.textSemi, fontSize: 14, color: c.onSurfaceSecondary },
  phone: { fontFamily: fonts.display, fontSize: 22, color: c.onSurface, letterSpacing: 1 },
  privacyRow: { flexDirection: "row", gap: 6, alignItems: "flex-start" },
  small: { flex: 1, fontFamily: fonts.text, fontSize: 12, color: c.muted, lineHeight: 17 },
  msg: { fontFamily: fonts.text, fontSize: 15, color: c.onSurfaceSecondary, fontStyle: "italic" },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  note: { fontFamily: fonts.text, fontSize: 14, color: c.onSurface },
  input: { height: 48, borderRadius: 12, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, paddingHorizontal: 12, fontFamily: fonts.text, fontSize: 15, color: c.onSurface },
}));
