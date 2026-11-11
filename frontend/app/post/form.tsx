import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Redirect, useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, Text, TextInput, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { useLister } from "@/src/lister";
import { useFocusedRefresh } from "@/src/useFocusedRefresh";
import { useAuth } from "@/src/auth";
import { storage } from "@/src/utils/storage";
import { Photo, PhotoPicker } from "@/src/components/PhotoPicker";
import { useToast } from "@/src/components/Toast";
import { Button, Checkbox, Chip, ScreenHeader } from "@/src/components/ui";
import { useMeta } from "@/src/data";
import { useLang } from "@/src/i18n";
import { fonts, makeStyles, useTheme } from "@/src/theme";

type Form = {
  purpose: "buy" | "rent";
  segment: string;
  type: string;
  locality_id: string;
  title_en: string;
  title_hi: string;
  description_en: string;
  price: string;
  bhk: string;
  bathrooms: string;
  area_sqft: string;
  furnishing: string;
  amenities: string[];
  address: string;
  postal_code: string;
};

const EMPTY: Form = { purpose: "buy", segment: "residential", type: "", locality_id: "", title_en: "", title_hi: "", description_en: "", price: "", bhk: "", bathrooms: "", area_sqft: "", furnishing: "", amenities: [], address: "", postal_code: "" };

export default function ListingForm() {
  const { as, id } = useLocalSearchParams<{ as?: string; id?: string }>();
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const { tx, pick } = useLang();
  const router = useRouter();
  const toast = useToast();
  const qc = useQueryClient();
  const { user, loading } = useAuth();
  const draftKey = `listing_draft.${user?.user_id ?? "guest"}.${id ?? "new"}`;
  const metaQuery = useMeta();
  const meta = metaQuery.data;
  const hydrated = useRef<string | null>(null);
  const submitting = useRef(false);
  const [uploading, setUploading] = useState(false);
  const [f, setF] = useState<Form>(EMPTY);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [declared, setDeclared] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formErr, setFormErr] = useState("");
  const [postedAs, setPostedAs] = useState<"owner" | "broker">(as === "broker" ? "broker" : "owner");

  const lister = useLister();
  useFocusedRefresh(lister.refetch, !!user && postedAs === "broker");
  const existing = useQuery({ queryKey: ["listing-edit", id, user?.user_id], queryFn: () => api<any>(`/listings/${id}/edit`), enabled: !!id && !!user });
  useEffect(() => {
    const p = existing.data;
    if (!p || hydrated.current === draftKey) return;
    hydrated.current = draftKey;
    // Hydrate the editable draft once the requested listing arrives from the API.
    setF({
      purpose: p.purpose, segment: p.segment, type: p.type, locality_id: p.locality_id, title_en: p.title_en, title_hi: p.title_hi === p.title_en ? "" : p.title_hi,
      description_en: p.description_en, price: String(p.price), bhk: p.bhk ? String(p.bhk) : "", bathrooms: p.bathrooms != null ? String(p.bathrooms) : "",
      area_sqft: String(p.area_sqft ?? ""), furnishing: p.furnishing ?? "", amenities: p.amenities ?? [],
      address: p.address ?? "", postal_code: p.postal_code ?? "",
    });
    setPhotos((p.photo_ids ?? []).map((pid: string, i: number) => ({ id: pid, url: p.images?.[i] ?? `/api/files/${pid}` })));
    setPostedAs(p.posted_by_role === "broker" ? "broker" : "owner");
  }, [existing.data, draftKey]);

  const segments = meta?.categories.filter((c) => c.kind === "segment") ?? [];
  const types = useMemo(() => (meta?.property_types ?? []).filter((t) => f.segment === "new-projects" || t.segment === f.segment), [meta, f.segment]);
  const selType = meta?.property_types.find((t) => t.slug === f.type);
  const set = (k: keyof Form, v: any) => setF((p) => ({ ...p, [k]: v }));

  const m = useMutation({
    mutationFn: async (body: any) => {
      const result = await api<any>(id ? `/listings/${id}` : "/listings", { method: id ? "PUT" : "POST", body });
      if (!result?.id || result.listing_status !== "pending_review") throw new Error("Could not confirm submission. Check My listings before trying again.");
      return result;
    },
    onSuccess: () => {
      storage.removeItem(draftKey);
      qc.invalidateQueries();
      toast.show(tx("Submitted for review. Check My listings for status.", "समीक्षा के लिए भेजा गया। स्थिति मेरी लिस्टिंग में देखें।"), "success");
      router.replace("/listings");
    },
    onSettled: () => { submitting.current = false; },
    onError: (e: any) => {
      setFormErr(e.message);
      toast.show(e.message, "error");
    },
  });

  const submit = () => {
    if (uploading || submitting.current || m.isPending) return;
    const e: Record<string, string> = {};
    if (f.postal_code && !/^[1-9]\d{5}$/.test(f.postal_code)) e.postal_code = "Enter a valid six-digit postal code";
    if (!f.type) e.type = tx("Choose a property type", "प्रॉपर्टी प्रकार चुनें");
    if (!f.locality_id) e.locality = tx("Choose a locality", "इलाका चुनें");
    if (f.title_en.trim().length < 5) e.title = tx("Title must be at least 5 characters", "शीर्षक कम से कम 5 अक्षर का हो");
    if (f.description_en.trim().length < 20) e.description = tx("Description must be at least 20 characters", "विवरण कम से कम 20 अक्षर का हो");
    const price = Number(f.price);
    if (!Number.isSafeInteger(price) || price < 1000 || price > 10000000000) e.price = tx("Enter a price from ₹1,000 to ₹10,000,000,000", "सही कीमत लिखें (कम से कम ₹1,000)");
    const area = Number(f.area_sqft);
    if (!Number.isSafeInteger(area) || area < 50 || area > 10000000) e.area = tx("Enter area from 50 to 10,000,000 sq.ft", "क्षेत्रफल वर्ग फुट में लिखें (कम से कम 50)");
    if (selType?.has_bhk && f.type !== "pg-hostel" && !f.bhk) e.bhk = tx("Choose BHK", "BHK चुनें");
    if (photos.length === 0) e.photos = tx("Add at least one photo", "कम से कम एक फ़ोटो जोड़ें");
    if (!declared) e.declared = tx("Please accept the declaration", "कृपया घोषणा स्वीकार करें");
    setErrors(e);
    setFormErr("");
    if (Object.keys(e).length) {
      setFormErr(tx("Please fix the highlighted fields", "कृपया चिह्नित फ़ील्ड ठीक करें"));
      return;
    }
    submitting.current = true;
    m.mutate({
      posted_as: postedAs, purpose: f.purpose, segment: f.segment, type: f.type, locality_id: f.locality_id,
      title_en: f.title_en.trim(), title_hi: f.title_hi.trim(), description_en: f.description_en.trim(),
      price, area_sqft: area, bhk: f.bhk ? parseInt(f.bhk, 10) : null, bathrooms: f.bathrooms ? parseInt(f.bathrooms, 10) : null,
      furnishing: f.furnishing || null, amenities: f.amenities, photo_ids: photos.map((p) => p.id), owner_declaration_accepted: declared,
      address: f.address.trim(), postal_code: f.postal_code || null,
    });
  };

  const saveDraft = async () => {
    const saved = await storage.setItem(draftKey, JSON.stringify({ version: 1, form: f, photos, postedAs }));
    toast.show(saved ? tx("Draft saved on this device", "ड्राफ्ट इस डिवाइस पर सुरक्षित है") : tx("Could not save draft", "ड्राफ्ट सुरक्षित नहीं हुआ"), saved ? "success" : "error");
  };
  const loadDraft = async () => {
    const raw = await storage.getItem(draftKey, null);
    if (typeof raw !== "string") { toast.show(tx("No saved draft on this device", "इस डिवाइस पर कोई ड्राफ्ट नहीं है"), "info"); return; }
    try {
      const draft = JSON.parse(raw);
      if (draft.version !== 1 || !draft.form || !Array.isArray(draft.photos) || !["owner", "broker"].includes(draft.postedAs)) throw new Error();
      if (Object.entries(EMPTY).some(([key, value]) => Array.isArray(value) ? !Array.isArray(draft.form[key]) || draft.form[key].some((v: unknown) => typeof v !== "string") : typeof draft.form[key] !== "string") || !["buy", "rent"].includes(draft.form.purpose) || draft.photos.length > 10 || draft.photos.some((p: any) => !p || typeof p.id !== "string" || typeof p.url !== "string")) throw new Error();
      setF({ ...EMPTY, ...draft.form }); setPhotos(draft.photos); setPostedAs(draft.postedAs); setDeclared(false);
      toast.show(tx("Draft restored. Review before submitting.", "ड्राफ्ट बहाल हुआ। जमा करने से पहले जाँचें।"), "success");
    } catch { toast.show(tx("This draft could not be read", "यह ड्राफ्ट पढ़ा नहीं जा सका"), "error"); }
  };

  if (loading || metaQuery.isLoading || (id && existing.isLoading)) return <View style={[styles.screen, { justifyContent: "center" }]}><ActivityIndicator color={colors.brandPrimary} /></View>;
  if (!user) return <Redirect href="/login" />;
  if (id && existing.isError) return <View style={styles.screen}><Text>{existing.error.message}</Text><Button label="Retry" onPress={() => existing.refetch()} /></View>;

  if (postedAs === "broker" && lister.isLoading) return <ActivityIndicator />;
  if (postedAs === "broker" && lister.isError) return <View style={styles.screen}><Text>Could not verify broker eligibility.</Text><Button label="Retry" onPress={() => lister.refetch()} /></View>;
  if (postedAs === "broker" && !lister.data?.can_post_as_broker) return <View style={styles.screen}><Text>Broker approval is required before submitting listings.</Text><Button label="Broker dashboard" onPress={() => router.replace("/broker")} /></View>;
  if (metaQuery.isError) return <View style={styles.screen}><Text>Could not load property options.</Text><Button label="Retry" onPress={() => metaQuery.refetch()} /></View>;
  if (id && ["expired", "sold_rented"].includes(existing.data?.listing_status)) return <View style={styles.screen}><Text>This listing can no longer be edited.</Text><Button label="My listings" onPress={() => router.replace("/listings")} /></View>;

  return (
    <View style={styles.screen}>
      <ScreenHeader title={id ? tx("Edit listing", "लिस्टिंग बदलें") : tx("New listing", "नई लिस्टिंग")} onBack={() => router.back()} topInset={insets.top} />
      <KeyboardAwareScrollView bottomOffset={24} contentContainerStyle={{ padding: 16, paddingBottom: insets.bottom + 32 }} keyboardShouldPersistTaps="handled">
        <View style={{ flexDirection: "row", gap: 8, marginBottom: 16 }}>
          <Button label={tx("Save draft", "ड्राफ्ट सहेजें")} onPress={saveDraft} variant="outline" disabled={m.isPending || uploading} style={{ flex: 1 }} />
          <Button label={tx("Restore draft", "ड्राफ्ट खोलें")} onPress={loadDraft} variant="outline" disabled={m.isPending || uploading} style={{ flex: 1 }} />
        </View>
        <View style={styles.roleBanner} testID="posting-as-banner">
          <Text style={styles.roleText}>{tx("Posting as", "पोस्टिंग")}: {postedAs === "broker" ? tx("Verified Broker", "सत्यापित ब्रोकर") : tx("Owner", "मालिक")}</Text>
        </View>
        {existing.data?.moderation?.note ? (
          <View style={styles.modNote} testID="moderation-note"><Text style={styles.modNoteText}>{tx("Reviewer note", "समीक्षक नोट")}: {existing.data.moderation.note}</Text></View>
        ) : null}

        <Section title={tx("Listing for", "लिस्टिंग")}>
          <Row>
            <Chip label={tx("Sell", "बेचें")} selected={f.purpose === "buy"} onPress={() => set("purpose", "buy")} testID="form-purpose-buy" />
            <Chip label={tx("Rent out", "किराए पर दें")} selected={f.purpose === "rent"} onPress={() => set("purpose", "rent")} testID="form-purpose-rent" />
          </Row>
        </Section>
        <Section title={tx("Category", "श्रेणी")}>
          <Row>
            {segments.map((s) => (
              <Chip key={s.slug} label={pick(s, "name")} selected={f.segment === s.slug} onPress={() => setF((p) => ({ ...p, segment: s.slug, type: "" }))} testID={`form-segment-${s.slug}`} />
            ))}
          </Row>
        </Section>
        <Section title={tx("Property type", "प्रॉपर्टी प्रकार")} error={errors.type}>
          <Row>
            {types.map((t) => (
              <Chip key={t.slug} label={pick(t, "name")} selected={f.type === t.slug} onPress={() => set("type", t.slug)} testID={`form-type-${t.slug}`} />
            ))}
          </Row>
        </Section>
        <Section title={tx("Locality in Ujjain", "उज्जैन में इलाका")} error={errors.locality}>
          <Row>
            {(meta?.localities ?? []).map((l) => (
              <Chip key={l.id} label={pick(l, "name")} selected={f.locality_id === l.id} onPress={() => set("locality_id", l.id)} testID={`form-locality-${l.slug}`} />
            ))}
          </Row>
        </Section>
        <Section title={tx("Title (English)", "शीर्षक (अंग्रेज़ी)")} error={errors.title}>
          <Input testID="form-title-en" value={f.title_en} onChangeText={(v) => set("title_en", v)} placeholder="e.g. 2 BHK flat near Nanakheda" maxLength={100} />
        </Section>
        <Section title={tx("Title (Hindi, optional)", "शीर्षक (हिंदी, वैकल्पिक)")}>
          <Input testID="form-title-hi" value={f.title_hi} onChangeText={(v) => set("title_hi", v)} placeholder="जैसे नानाखेड़ा के पास 2 BHK फ्लैट" maxLength={100} />
        </Section>
        <Section title={f.purpose === "rent" ? tx("Monthly rent (₹)", "मासिक किराया (₹)") : tx("Expected price (₹)", "अपेक्षित कीमत (₹)")} error={errors.price}>
          <Input testID="form-price" value={f.price} onChangeText={(v) => set("price", v.replace(/\D/g, ""))} keyboardType="number-pad" placeholder="3500000" maxLength={11} />
        </Section>
        <Section title={tx("Area (sq.ft)", "क्षेत्रफल (वर्ग फुट)")} error={errors.area}>
          <Input testID="form-area" value={f.area_sqft} onChangeText={(v) => set("area_sqft", v.replace(/\D/g, ""))} keyboardType="number-pad" placeholder="1100" maxLength={8} />
        </Section>
        {selType?.has_bhk && (
          <Section title="BHK" error={errors.bhk}>
            <Row>
              {["1", "2", "3", "4", "5"].map((b) => (
                <Chip key={b} label={`${b} BHK`} selected={f.bhk === b} onPress={() => set("bhk", b)} testID={`form-bhk-${b}`} />
              ))}
            </Row>
          </Section>
        )}
        {f.segment !== "plot-land" && (
          <>
            <Section title={tx("Bathrooms", "बाथरूम")}>
              <Row>
                {["1", "2", "3", "4"].map((b) => (
                  <Chip key={b} label={b} selected={f.bathrooms === b} onPress={() => set("bathrooms", f.bathrooms === b ? "" : b)} testID={`form-bath-${b}`} />
                ))}
              </Row>
            </Section>
            <Section title={tx("Furnishing", "फर्निशिंग")}>
              <Row>
                {([["furnished", "Furnished", "फर्निश्ड"], ["semi-furnished", "Semi-furnished", "सेमी-फर्निश्ड"], ["unfurnished", "Unfurnished", "अनफर्निश्ड"]] as const).map(([k, e, h]) => (
                  <Chip key={k} label={tx(e, h)} selected={f.furnishing === k} onPress={() => set("furnishing", f.furnishing === k ? "" : k)} testID={`form-furnish-${k}`} />
                ))}
              </Row>
            </Section>
          </>
        )}
        <Section title={tx("Amenities", "सुविधाएं")}>
          <Row>
            {(meta?.amenities ?? []).map((a) => (
              <Chip key={a.slug} label={pick(a, "name")} selected={f.amenities.includes(a.slug)}
                onPress={() => set("amenities", f.amenities.includes(a.slug) ? f.amenities.filter((x) => x !== a.slug) : [...f.amenities, a.slug])} testID={`form-amenity-${a.slug}`} />
            ))}
          </Row>
        </Section>
        <Section title={tx("Description", "विवरण")} error={errors.description}>
          <Input testID="form-description" value={f.description_en} onChangeText={(v) => set("description_en", v)} multiline style={{ minHeight: 110, paddingTop: 12, textAlignVertical: "top" }}
            placeholder={tx("Describe the property, road access, nearby landmarks…", "प्रॉपर्टी, सड़क, आसपास के स्थानों के बारे में लिखें…")} maxLength={2000} />
        </Section>
        <Section title={tx("Photos", "फ़ोटो")} error={errors.photos}>
          <PhotoPicker photos={photos} onChange={setPhotos} disabled={m.isPending} onBusyChange={setUploading} />
        </Section>

        <Section title={tx("Address · Ujjain, Madhya Pradesh", "पता · उज्जैन, मध्य प्रदेश")} error={errors.postal_code}>
          <TextInput accessibilityLabel="Property address" value={f.address} onChangeText={v => set("address", v)} placeholder="Address (shown publicly)" maxLength={300} />
          <TextInput accessibilityLabel="Postal code" value={f.postal_code} onChangeText={v => set("postal_code", v)} placeholder="Postal code" keyboardType="number-pad" maxLength={6} />
        </Section>

        <View style={[styles.declare, errors.declared && { borderColor: colors.error }]}>
          <Checkbox checked={declared} onToggle={() => setDeclared(!declared)} testID="form-declaration-checkbox"
            label={postedAs === "broker"
              ? tx("I declare I am authorised by the owner to list this property and the details are true.", "मैं घोषणा करता/करती हूँ कि मुझे मालिक ने यह प्रॉपर्टी लिस्ट करने का अधिकार दिया है और विवरण सही हैं।")
              : tx("I declare I am the owner (or legally authorised) and the details are true.", "मैं घोषणा करता/करती हूँ कि मैं मालिक (या कानूनी रूप से अधिकृत) हूँ और विवरण सही हैं।")} />
          <Text style={styles.disclaimer}>{tx("LANDVILLA reviews listings for quality, but this is not a check of title, ownership, approvals or legal status.", "LANDVILLA गुणवत्ता के लिए लिस्टिंग जाँचता है, पर यह मालिकाना हक़, स्वामित्व, अनुमतियों या कानूनी स्थिति की जाँच नहीं है।")}</Text>
          <Text style={styles.disclaimer}>
            <Text style={{ color: colors.brandPrimary }} onPress={() => router.push("/legal/terms")} testID="form-terms-link">{tx("Terms", "नियम")}</Text>
            {"  ·  "}
            <Text style={{ color: colors.brandPrimary }} onPress={() => router.push("/legal/privacy")} testID="form-privacy-link">{tx("Privacy Policy", "गोपनीयता नीति")}</Text>
          </Text>
        </View>
        {!!formErr && <Text style={styles.formErr} testID="form-error">{formErr}</Text>}
        <Button label={id ? tx("Resubmit for review", "फिर से समीक्षा हेतु भेजें") : tx("Submit for review", "समीक्षा हेतु भेजें")} onPress={submit} disabled={uploading} loading={m.isPending} testID="form-submit-btn" style={{ marginTop: 16 }} />
      </KeyboardAwareScrollView>
    </View>
  );
}

function Section({ title, children, error }: { title: string; children: React.ReactNode; error?: string }) {
  const styles = useStyles();
  return (
    <View style={styles.section}>
      <Text style={styles.label}>{title}</Text>
      {children}
      {!!error && <Text style={styles.err}>{error}</Text>}
    </View>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>{children}</View>;
}

function Input(props: React.ComponentProps<typeof TextInput>) {
  const styles = useStyles();
  const { colors } = useTheme();
  return <TextInput placeholderTextColor={colors.muted} {...props} style={[styles.input, props.style]} />;
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surface },
  roleBanner: { padding: 12, borderRadius: 12, backgroundColor: c.brandTertiary },
  roleText: { fontFamily: fonts.textSemi, fontSize: 14, color: c.onBrandTertiary },
  modNote: { marginTop: 12, padding: 12, borderRadius: 12, borderWidth: 1, borderColor: c.error },
  modNoteText: { fontFamily: fonts.textMedium, fontSize: 14, color: c.error },
  section: { marginTop: 24 },
  label: { fontFamily: fonts.textSemi, fontSize: 14, color: c.onSurfaceSecondary, marginBottom: 8 },
  input: { minHeight: 50, borderRadius: 12, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, paddingHorizontal: 14, fontFamily: fonts.text, fontSize: 16, color: c.onSurface },
  err: { color: c.error, fontFamily: fonts.text, fontSize: 13, marginTop: 6 },
  declare: { marginTop: 24, padding: 12, borderRadius: 12, borderWidth: 1, borderColor: c.border },
  disclaimer: { fontFamily: fonts.text, fontSize: 12, color: c.muted, lineHeight: 17 },
  formErr: { color: c.error, fontFamily: fonts.textMedium, fontSize: 14, marginTop: 16 },
}));
