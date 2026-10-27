import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as DocumentPicker from "expo-document-picker";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { uploadFile } from "@/src/components/PhotoPicker";
import { useToast } from "@/src/components/Toast";
import { Button, Checkbox, ScreenHeader } from "@/src/components/ui";
import { useLang } from "@/src/i18n";
import { fonts, makeStyles, useTheme } from "@/src/theme";

type Doc = { id: string; name: string };

export default function BrokerApply() {
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const { tx } = useLang();
  const router = useRouter();
  const toast = useToast();
  const qc = useQueryClient();
  const [fullName, setFullName] = useState("");
  const [firm, setFirm] = useState("");
  const [phone, setPhone] = useState("");
  const [rera, setRera] = useState("");
  const [docs, setDocs] = useState<Doc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [declared, setDeclared] = useState(false);
  const [err, setErr] = useState("");

  const addDoc = async () => {
    const r = await DocumentPicker.getDocumentAsync({ type: ["application/pdf", "image/jpeg", "image/png", "image/webp"], copyToCacheDirectory: true });
    if (r.canceled) return;
    const a = r.assets[0];
    if (a.size && a.size > 10 * 1024 * 1024) return toast.show(tx("File too large (max 10 MB)", "फ़ाइल बहुत बड़ी है (अधिकतम 10 MB)"), "error");
    setUploading(true);
    try {
      const up = await uploadFile({ uri: a.uri, name: a.name, mimeType: a.mimeType }, "broker_doc");
      setDocs((d) => [...d, { id: up.id, name: a.name }]);
    } catch (e: any) {
      toast.show(e.message, "error");
    } finally {
      setUploading(false);
    }
  };

  const m = useMutation({
    mutationFn: () => api("/broker/apply", { method: "POST", body: { full_name: fullName.trim(), firm_name: firm.trim(), phone, rera_number: rera.trim(), document_ids: docs.map((d) => d.id), declaration_accepted: declared } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["lister"] });
      toast.show(tx("Broker request submitted for admin review", "ब्रोकर अनुरोध एडमिन समीक्षा के लिए भेजा गया"), "success");
      router.back();
    },
    onError: (e: any) => setErr(e.message),
  });

  const submit = () => {
    setErr("");
    if (fullName.trim().length < 2) return setErr(tx("Enter your full name", "अपना पूरा नाम लिखें"));
    if (!/^[6-9]\d{9}$/.test(phone)) return setErr(tx("Enter a valid 10-digit mobile number", "सही 10 अंकों का मोबाइल नंबर लिखें"));
    if (docs.length === 0) return setErr(tx("Upload at least one identity document", "कम से कम एक पहचान दस्तावेज़ अपलोड करें"));
    if (!declared) return setErr(tx("Please accept the declaration", "कृपया घोषणा स्वीकार करें"));
    m.mutate();
  };

  return (
    <View style={styles.screen}>
      <ScreenHeader title={tx("Broker verification", "ब्रोकर सत्यापन")} onBack={() => router.back()} topInset={insets.top} />
      <KeyboardAwareScrollView bottomOffset={24} contentContainerStyle={{ padding: 16, paddingBottom: insets.bottom + 32 }} keyboardShouldPersistTaps="handled">
        <Text style={styles.intro}>{tx("Brokers must be verified by our team before posting. Documents are stored privately and seen only by LANDVILLA admins.", "पोस्ट करने से पहले ब्रोकर का सत्यापन ज़रूरी है। दस्तावेज़ निजी रूप से रखे जाते हैं और केवल LANDVILLA एडमिन देखते हैं।")}</Text>
        <Label text={tx("Full name (as on ID)", "पूरा नाम (पहचान पत्र अनुसार)")} />
        <TextInput testID="broker-name-input" value={fullName} onChangeText={setFullName} style={styles.input} placeholderTextColor={colors.muted} />
        <Label text={tx("Firm / agency name (optional)", "फर्म / एजेंसी नाम (वैकल्पिक)")} />
        <TextInput testID="broker-firm-input" value={firm} onChangeText={setFirm} style={styles.input} placeholderTextColor={colors.muted} />
        <Label text={tx("Mobile number", "मोबाइल नंबर")} />
        <TextInput testID="broker-phone-input" value={phone} onChangeText={(v) => setPhone(v.replace(/\D/g, "").slice(0, 10))} keyboardType="phone-pad" style={styles.input} placeholder="98XXXXXXXX" placeholderTextColor={colors.muted} />
        <Label text={tx("MP RERA agent registration no. (if any)", "MP RERA एजेंट पंजीकरण सं. (यदि हो)")} />
        <TextInput testID="broker-rera-input" value={rera} onChangeText={setRera} style={styles.input} autoCapitalize="characters" placeholderTextColor={colors.muted} />
        <Text style={styles.small}>{tx("RERA status is recorded separately and stays 'unverified' until our team checks it.", "RERA स्थिति अलग दर्ज होती है और हमारी जाँच तक 'असत्यापित' रहती है।")}</Text>

        <Label text={tx("Identity documents (Aadhaar/PAN/agency proof)", "पहचान दस्तावेज़ (आधार/पैन/एजेंसी प्रमाण)")} />
        {docs.map((d) => (
          <View key={d.id} style={styles.docRow}>
            <Ionicons name="document-text-outline" size={20} color={colors.brandPrimary} />
            <Text style={styles.docName} numberOfLines={1}>{d.name}</Text>
            <Pressable hitSlop={8} onPress={() => setDocs(docs.filter((x) => x.id !== d.id))} testID={`broker-doc-remove-${d.id}`}>
              <Ionicons name="close-circle" size={20} color={colors.muted} />
            </Pressable>
          </View>
        ))}
        {docs.length < 5 && (
          <Pressable style={styles.addDoc} onPress={addDoc} disabled={uploading} testID="broker-add-doc-btn">
            {uploading ? <ActivityIndicator color={colors.brandPrimary} /> : <Ionicons name="cloud-upload-outline" size={22} color={colors.brandPrimary} />}
            <Text style={styles.addDocText}>{tx("Upload document (PDF or image)", "दस्तावेज़ अपलोड करें (PDF या फ़ोटो)")}</Text>
          </Pressable>
        )}
        <Checkbox checked={declared} onToggle={() => setDeclared(!declared)} testID="broker-declaration-checkbox"
          label={tx("I confirm these documents are genuine and belong to me.", "मैं पुष्टि करता/करती हूँ कि ये दस्तावेज़ असली हैं और मेरे हैं।")} />
        {!!err && <Text style={styles.err} testID="broker-form-error">{err}</Text>}
        <Button label={tx("Submit for verification", "सत्यापन हेतु भेजें")} onPress={submit} loading={m.isPending} testID="broker-submit-btn" style={{ marginTop: 8 }} />
      </KeyboardAwareScrollView>
    </View>
  );
}

function Label({ text }: { text: string }) {
  const styles = useStyles();
  return <Text style={styles.label}>{text}</Text>;
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surface },
  intro: { fontFamily: fonts.text, fontSize: 14, color: c.onSurfaceTertiary, lineHeight: 20, padding: 12, borderRadius: 12, backgroundColor: c.brandTertiary },
  label: { fontFamily: fonts.textSemi, fontSize: 14, color: c.onSurfaceSecondary, marginTop: 20, marginBottom: 8 },
  input: { height: 50, borderRadius: 12, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, paddingHorizontal: 14, fontFamily: fonts.text, fontSize: 16, color: c.onSurface },
  small: { fontFamily: fonts.text, fontSize: 12, color: c.muted, marginTop: 6 },
  docRow: { flexDirection: "row", alignItems: "center", gap: 8, padding: 12, borderRadius: 12, borderWidth: 1, borderColor: c.border, marginBottom: 8 },
  docName: { flex: 1, fontFamily: fonts.textMedium, fontSize: 14, color: c.onSurface },
  addDoc: { flexDirection: "row", alignItems: "center", gap: 8, padding: 14, borderRadius: 12, borderWidth: 1.5, borderStyle: "dashed", borderColor: c.brandPrimary, marginBottom: 8 },
  addDocText: { fontFamily: fonts.textMedium, fontSize: 14, color: c.brandPrimary },
  err: { color: c.error, fontFamily: fonts.textMedium, fontSize: 14, marginVertical: 8 },
}));
