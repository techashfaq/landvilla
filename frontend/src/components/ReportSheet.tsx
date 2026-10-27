import { useMutation } from "@tanstack/react-query";
import React, { useState } from "react";
import { ScrollView, Text, TextInput, View } from "react-native";

import { api } from "@/src/api";
import { Sheet } from "@/src/components/Sheet";
import { useToast } from "@/src/components/Toast";
import { Button, Chip } from "@/src/components/ui";
import { useLang } from "@/src/i18n";
import { fonts, makeStyles, useTheme } from "@/src/theme";

const REASONS = [
  ["fake_listing", "Fake listing", "नकली लिस्टिंग"],
  ["wrong_info", "Wrong information", "गलत जानकारी"],
  ["spam", "Spam", "स्पैम"],
  ["abuse", "Abusive behaviour", "अपमानजनक व्यवहार"],
  ["fraud", "Fraud / scam", "धोखाधड़ी"],
  ["other", "Other", "अन्य"],
] as const;

/** Report sheet for a listing (`path=/properties/{id}/report`) or a conversation (`/enquiries/{id}/report-user`). */
export function ReportSheet({ visible, onClose, path, title }: { visible: boolean; onClose: () => void; path: string; title: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { tx } = useLang();
  const toast = useToast();
  const [reason, setReason] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");
  const m = useMutation({
    mutationFn: () => api(path, { method: "POST", body: { reason, note } }),
    onSuccess: () => { toast.show(tx("Report sent. Our team will review it.", "रिपोर्ट भेजी गई। हमारी टीम इसकी समीक्षा करेगी।"), "success"); setReason(null); setNote(""); onClose(); },
    onError: (e: any) => setErr(e.message),
  });
  return (
    <Sheet visible={visible} onClose={onClose} title={title} testID="report-sheet"
      footer={<Button label={tx("Send report", "रिपोर्ट भेजें")} disabled={!reason} loading={m.isPending} onPress={() => { setErr(""); m.mutate(); }} testID="report-submit-btn" />}>
      <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 16, gap: 12 }} keyboardShouldPersistTaps="handled">
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {REASONS.map(([k, e, h]) => <Chip key={k} label={tx(e, h)} selected={reason === k} onPress={() => setReason(k)} testID={`report-reason-${k}`} />)}
        </View>
        <TextInput testID="report-note-input" value={note} onChangeText={setNote} multiline maxLength={500} placeholder={tx("Details (optional)", "विवरण (वैकल्पिक)")} placeholderTextColor={colors.muted} style={styles.input} />
        {!!err && <Text style={styles.err} testID="report-error">{err}</Text>}
      </ScrollView>
    </Sheet>
  );
}

const useStyles = makeStyles((c) => ({
  input: { minHeight: 80, borderRadius: 12, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, padding: 12, fontFamily: fonts.text, fontSize: 15, color: c.onSurface, textAlignVertical: "top" },
  err: { color: c.error, fontFamily: fonts.textMedium },
}));
