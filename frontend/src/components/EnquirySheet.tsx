import { useMutation, useQueryClient } from "@tanstack/react-query";
import React, { useEffect, useState } from "react";
import { ScrollView, Text, TextInput, View } from "react-native";

import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Sheet } from "@/src/components/Sheet";
import { useToast } from "@/src/components/Toast";
import { Button, Checkbox, Chip } from "@/src/components/ui";
import { useLang } from "@/src/i18n";
import { fonts, makeStyles, useTheme } from "@/src/theme";

export function EnquirySheet({ visible, onClose, propertyId }: { visible: boolean; onClose: () => void; propertyId: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { t, tx } = useLang();
  const { user } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [intent, setIntent] = useState<"info" | "site_visit" | "callback">("info");
  const [consent, setConsent] = useState(false);
  const [errors, setErrors] = useState<{ name?: string; phone?: string; form?: string }>({});

  useEffect(() => {
    if (visible) {
      setName((n) => n || user?.name || "");
      setErrors({});
    }
  }, [visible, user]);

  const m = useMutation({
    mutationFn: () => api("/enquiries", { method: "POST", body: { property_id: propertyId, name, phone, message, intent, share_phone_consent: consent } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["enquiries"] });
      toast.show(t("enquirySent"), "success");
      setMessage("");
      onClose();
    },
    onError: (e: any) => {
      setErrors({ form: e.message });
      toast.show(e.message, "error");
    },
  });

  const submit = () => {
    const errs: typeof errors = {};
    if (!name.trim()) errs.name = t("nameError");
    else if (name.trim().length < 2) errs.name = t("nameShort");
    const digits = phone.replace(/\D/g, "").replace(/^91(?=\d{10}$)/, "");
    if (!/^[6-9]\d{9}$/.test(digits)) errs.phone = t("phoneError");
    setErrors(errs);
    if (Object.keys(errs).length === 0) m.mutate();
  };

  return (
    <Sheet
      visible={visible}
      onClose={onClose}
      title={t("enquireNow")}
      testID="enquiry-sheet"
      footer={<Button label={t("sendEnquiry")} onPress={submit} loading={m.isPending} testID="enquiry-submit-btn" icon="paper-plane-outline" />}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        {errors.form && <Text style={styles.formErr} testID="enquiry-form-error">{errors.form}</Text>}
        <Text style={styles.label}>{t("iWantTo")}</Text>
        <View style={styles.row}>
          <Chip label={t("intentInfo")} selected={intent === "info"} onPress={() => setIntent("info")} testID="enquiry-intent-info" />
          <Chip label={t("intentVisit")} selected={intent === "site_visit"} onPress={() => setIntent("site_visit")} testID="enquiry-intent-visit" />
          <Chip label={t("intentCallback")} selected={intent === "callback"} onPress={() => setIntent("callback")} testID="enquiry-intent-callback" />
        </View>
        <Text style={styles.label}>{t("yourName")}</Text>
        <TextInput
          testID="enquiry-name-input"
          value={name}
          onChangeText={setName}
          style={[styles.input, errors.name && styles.inputErr]}
          placeholderTextColor={colors.muted}
          placeholder={t("yourName")}
          autoComplete="name"
        />
        {errors.name && <Text style={styles.err} testID="enquiry-name-error">{errors.name}</Text>}
        <Text style={styles.label}>{t("mobile")}</Text>
        <View style={[styles.input, styles.phoneWrap, errors.phone && styles.inputErr]}>
          <Text style={styles.prefix}>+91</Text>
          <TextInput
            testID="enquiry-phone-input"
            value={phone}
            onChangeText={(v) => setPhone(v.replace(/[^\d]/g, "").slice(0, 10))}
            keyboardType="phone-pad"
            style={styles.phoneInput}
            placeholder="98XXXXXXXX"
            placeholderTextColor={colors.muted}
            maxLength={10}
          />
        </View>
        {errors.phone && <Text style={styles.err} testID="enquiry-phone-error">{errors.phone}</Text>}
        <Text style={styles.label}>{t("message")}</Text>
        <TextInput
          testID="enquiry-message-input"
          value={message}
          onChangeText={setMessage}
          style={[styles.input, styles.textarea]}
          multiline
          maxLength={500}
          placeholderTextColor={colors.muted}
          placeholder={t("message")}
        />
        <Checkbox
          checked={consent}
          onToggle={() => setConsent(!consent)}
          testID="enquiry-consent-checkbox"
          label={tx("I agree to share my phone number with this property owner/broker for this enquiry.", "मैं इस पूछताछ के लिए अपना फ़ोन नंबर इस प्रॉपर्टी के मालिक/ब्रोकर के साथ साझा करने के लिए सहमत हूँ।")}
        />
        <Text style={styles.privacy}>
          {tx("Without consent, your number stays hidden and the lister can reply only in the app.", "सहमति के बिना आपका नंबर छिपा रहेगा और लिस्टर केवल ऐप में जवाब दे सकेगा।")}
        </Text>
      </ScrollView>
    </Sheet>
  );
}

const useStyles = makeStyles((c) => ({
  content: { paddingHorizontal: 16, paddingBottom: 16 },
  label: { fontFamily: fonts.textSemi, fontSize: 14, color: c.onSurfaceSecondary, marginTop: 16, marginBottom: 8 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  input: {
    minHeight: 50,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.surfaceSecondary,
    paddingHorizontal: 14,
    fontFamily: fonts.text,
    fontSize: 16,
    color: c.onSurface,
  },
  inputErr: { borderColor: c.error },
  phoneWrap: { flexDirection: "row", alignItems: "center", gap: 8 },
  prefix: { fontFamily: fonts.textSemi, fontSize: 16, color: c.onSurfaceTertiary },
  phoneInput: { flex: 1, height: 50, fontFamily: fonts.text, fontSize: 16, color: c.onSurface },
  textarea: { minHeight: 90, paddingTop: 12, textAlignVertical: "top" },
  err: { color: c.error, fontFamily: fonts.text, fontSize: 13, marginTop: 4 },
  formErr: { color: c.error, fontFamily: fonts.textMedium, fontSize: 14, marginTop: 8, padding: 12, borderRadius: 12, backgroundColor: c.brandTertiary },
  privacy: { fontFamily: fonts.text, fontSize: 12, color: c.muted, marginTop: 4, lineHeight: 17 },
}));
