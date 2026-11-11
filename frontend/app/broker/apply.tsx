import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as DocumentPicker from "expo-document-picker";
import { Redirect, useRouter } from "expo-router";
import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAuth } from "@/src/auth";
import { useMeta } from "@/src/data";
import { useBrokerDashboard } from "@/src/lister";
import { useFocusedRefresh } from "@/src/useFocusedRefresh";
import { api } from "@/src/api";
import { uploadFile } from "@/src/components/PhotoPicker";
import { useToast } from "@/src/components/Toast";
import { Button, Checkbox, Chip, EmptyState, ScreenHeader } from "@/src/components/ui";
import { useLang } from "@/src/i18n";
import { fonts, makeStyles, useTheme } from "@/src/theme";

type Doc = { id: string; name: string };

export default function BrokerApply() {
  const { user, loading } = useAuth();
  if (loading) return <ActivityIndicator />;
  if (!user) return <Redirect href="/login" />;
  return <BrokerApplicationForm key={user.user_id} />;
}

function BrokerApplicationForm() {
  const { user, loading } = useAuth();
  const profile = useBrokerDashboard();
  const meta = useMeta();
  useFocusedRefresh(profile.refetch, !!user);
  const initialized = useRef<string | null>(null);
  const locked = useRef(false);
  const [locality, setLocality] = useState("");
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
  const [failedDoc, setFailedDoc] = useState<DocumentPicker.DocumentPickerAsset | null>(null);
  const [uploading, setUploading] = useState(false);
  const [declared, setDeclared] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    const p = profile.data?.application;
    if (!p || !user || initialized.current === user.user_id) return;
    initialized.current = user.user_id;
    setFullName(p.full_name); setFirm(p.firm_name || ""); setPhone(p.phone); setRera(p.rera_number || ""); setLocality(p.locality_id || ""); setDocs(p.documents);
  }, [profile.data, user]);

  const addDoc = async (retry = false) => {
    if (locked.current || uploading || docs.length >= 5) return;
    locked.current = true;
    setUploading(true);
    try {
      let a = retry ? failedDoc : null;
      if (!a) {
        const r = await DocumentPicker.getDocumentAsync({ type: ["application/pdf", "image/jpeg", "image/png", "image/webp"], copyToCacheDirectory: true });
        if (r.canceled) return;
        a = r.assets[0];
      }
      if (a.size && a.size > 10 * 1024 * 1024) return toast.show(tx("File too large (max 10 MB)", "फ़ाइल बहुत बड़ी है (अधिकतम 10 MB)"), "error");
      setFailedDoc(a);
      const up = await uploadFile({ uri: a.uri, name: a.name, mimeType: a.mimeType }, "broker_doc");
      const name = a.name;
      setDocs((d) => [...d.filter(doc => doc.id !== up.id), { id: up.id, name }]);
      setFailedDoc(null);
    } catch (e: any) {
      toast.show(e.message, "error");
    } finally {
      setUploading(false);
      locked.current = false;
    }
  };

  const m = useMutation({
    mutationFn: async () => {
      const result = await api<{ status: string }>("/broker/apply", { method: "POST", body: { locality_id: locality, full_name: fullName.trim(), firm_name: firm.trim(), phone, rera_number: rera.trim(), document_ids: docs.map((d) => d.id), declaration_accepted: declared } });
      if (result?.status !== "pending") throw new Error("Could not confirm submission. Refresh your application status before retrying.");
      return result;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["lister"] });
      qc.invalidateQueries({ queryKey: ["broker-dashboard"] });
      toast.show(tx("Broker request submitted for admin review", "ब्रोकर अनुरोध एडमिन समीक्षा के लिए भेजा गया"), "success");
      router.replace("/broker");
    },
    onError: (e: any) => { setErr(e.message); void profile.refetch(); },
    onSettled: () => { locked.current = false; },
  });

  const submit = () => {
    if (locked.current || uploading || m.isPending) return;
    setErr("");
    if (fullName.trim().length < 2) return setErr(tx("Enter your full name", "अपना पूरा नाम लिखें"));
    if (!/^[6-9]\d{9}$/.test(phone)) return setErr(tx("Enter a valid 10-digit mobile number", "सही 10 अंकों का मोबाइल नंबर लिखें"));
    if (!locality) return setErr("Choose your operating locality in Ujjain");
    if (docs.length === 0) return setErr(tx("Upload at least one identity document", "कम से कम एक पहचान दस्तावेज़ अपलोड करें"));
    if (!declared) return setErr(tx("Please accept the declaration", "कृपया घोषणा स्वीकार करें"));
    locked.current = true;
    m.mutate();
  };

  if (loading) return <ActivityIndicator />;
  if (!user) return <Redirect href="/login" />;
  if (profile.isLoading || meta.isLoading) return <ActivityIndicator />;
  if (profile.isError || meta.isError) return <EmptyState icon="cloud-offline-outline" title="Could not load application details" cta="Retry" onPress={() => { void profile.refetch(); void meta.refetch(); }} />;
  if (profile.data?.application && profile.data.application.status !== "rejected") return <Redirect href="/broker" />;

  return (
    <View style={styles.screen}>
      <ScreenHeader title={tx("Broker verification", "ब्रोकर सत्यापन")} onBack={() => router.back()} topInset={insets.top} />
      <KeyboardAwareScrollView bottomOffset={24} contentContainerStyle={{ padding: 16, paddingBottom: insets.bottom + 32 }} keyboardShouldPersistTaps="handled">
        <Text style={styles.intro}>{tx("Brokers must be verified by our team before posting. Documents are stored privately and seen only by LANDVILLA admins.", "पोस्ट करने से पहले ब्रोकर का सत्यापन ज़रूरी है। दस्तावेज़ निजी रूप से रखे जाते हैं और केवल LANDVILLA एडमिन देखते हैं।")}</Text>
        {!!profile.data?.application?.admin_note && <Text style={styles.err}>Reviewer note: {profile.data.application.admin_note}</Text>}
        <Label text={tx("Full name (as on ID)", "पूरा नाम (पहचान पत्र अनुसार)")} />
        <TextInput testID="broker-name-input" maxLength={80} value={fullName} onChangeText={setFullName} style={styles.input} placeholderTextColor={colors.muted} />
        <Label text={tx("Firm / agency name (optional)", "फर्म / एजेंसी नाम (वैकल्पिक)")} />
        <TextInput testID="broker-firm-input" maxLength={120} value={firm} onChangeText={setFirm} style={styles.input} placeholderTextColor={colors.muted} />
        <Label text={tx("Mobile number", "मोबाइल नंबर")} />
        <TextInput testID="broker-phone-input" value={phone} onChangeText={(v) => setPhone(v.replace(/\D/g, "").slice(0, 10))} keyboardType="phone-pad" style={styles.input} placeholder="98XXXXXXXX" placeholderTextColor={colors.muted} />
        <Label text={tx("MP RERA agent registration no. (if any)", "MP RERA एजेंट पंजीकरण सं. (यदि हो)")} />
        <TextInput testID="broker-rera-input" maxLength={60} value={rera} onChangeText={setRera} style={styles.input} autoCapitalize="characters" placeholderTextColor={colors.muted} />
        <Text style={styles.small}>{tx("RERA status is recorded separately and stays 'unverified' until our team checks it.", "RERA स्थिति अलग दर्ज होती है और हमारी जाँच तक 'असत्यापित' रहती है।")}</Text>

        <Label text="Operating locality in Ujjain" />
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>{meta.data?.localities.map(l => <Chip key={l.id} label={l.name_en} selected={locality === l.id} onPress={() => setLocality(l.id)} />)}</View>
        <Label text={tx("Identity documents (Aadhaar/PAN/agency proof)", "पहचान दस्तावेज़ (आधार/पैन/एजेंसी प्रमाण)")} />
        {docs.map((d) => (
          <View key={d.id} style={styles.docRow}>
            <Ionicons name="document-text-outline" size={20} color={colors.brandPrimary} />
            <Text style={styles.docName} numberOfLines={1}>{d.name}</Text>
            <Pressable disabled={uploading || m.isPending} accessibilityLabel="Remove document" hitSlop={8} onPress={() => setDocs(docs.filter((x) => x.id !== d.id))} testID={`broker-doc-remove-${d.id}`}>
              <Ionicons name="close-circle" size={20} color={colors.muted} />
            </Pressable>
          </View>
        ))}
        {docs.length < 5 && (
          <Pressable style={styles.addDoc} onPress={() => addDoc()} disabled={uploading || m.isPending} testID="broker-add-doc-btn">
            {uploading ? <ActivityIndicator color={colors.brandPrimary} /> : <Ionicons name="cloud-upload-outline" size={22} color={colors.brandPrimary} />}
            <Text style={styles.addDocText}>{tx("Upload document (PDF or image)", "दस्तावेज़ अपलोड करें (PDF या फ़ोटो)")}</Text>
          </Pressable>
        )}
        {failedDoc && <Button label="Retry failed document upload" variant="outline" onPress={() => addDoc(true)} disabled={uploading || m.isPending || docs.length >= 5} />}
        <Checkbox checked={declared} onToggle={() => setDeclared(!declared)} testID="broker-declaration-checkbox"
          label={tx("I confirm these documents are genuine and belong to me.", "मैं पुष्टि करता/करती हूँ कि ये दस्तावेज़ असली हैं और मेरे हैं।")} />
        {!!err && <Text style={styles.err} testID="broker-form-error">{err}</Text>}
        <Button label={tx("Submit for verification", "सत्यापन हेतु भेजें")} onPress={submit} disabled={uploading} loading={m.isPending} testID="broker-submit-btn" style={{ marginTop: 8 }} />
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
