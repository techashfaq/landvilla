import React, { useEffect, useState } from "react";
import { ScrollView, Text, View } from "react-native";

import { Sheet } from "@/src/components/Sheet";
import { Button, Chip } from "@/src/components/ui";
import { Meta } from "@/src/data";
import { useLang } from "@/src/i18n";
import { fonts, makeStyles } from "@/src/theme";

export type Filters = {
  purpose: "buy" | "rent";
  segment?: string;
  type?: string;
  locality: string[];
  zone?: string;
  budget?: string; // key into BUDGETS
  bhk: string[];
  sort: "newest" | "price_asc" | "price_desc";
};

export const DEFAULT_FILTERS: Filters = { purpose: "buy", locality: [], bhk: [], sort: "newest" };

export const BUDGETS: Record<"buy" | "rent", { key: string; en: string; hi: string; min?: number; max?: number }[]> = {
  buy: [
    { key: "b1", en: "Under ₹25 L", hi: "₹25 लाख से कम", max: 2500000 },
    { key: "b2", en: "₹25 L – 50 L", hi: "₹25–50 लाख", min: 2500000, max: 5000000 },
    { key: "b3", en: "₹50 L – 1 Cr", hi: "₹50 लाख–1 करोड़", min: 5000000, max: 10000000 },
    { key: "b4", en: "Above ₹1 Cr", hi: "₹1 करोड़ से ज़्यादा", min: 10000000 },
  ],
  rent: [
    { key: "r1", en: "Under ₹10k", hi: "₹10 हज़ार से कम", max: 10000 },
    { key: "r2", en: "₹10k – 20k", hi: "₹10–20 हज़ार", min: 10000, max: 20000 },
    { key: "r3", en: "₹20k – 40k", hi: "₹20–40 हज़ार", min: 20000, max: 40000 },
    { key: "r4", en: "Above ₹40k", hi: "₹40 हज़ार से ज़्यादा", min: 40000 },
  ],
};

const BHKS = ["1", "2", "3", "4+"];

export function FilterSheet({
  visible,
  onClose,
  value,
  onApply,
  meta,
}: {
  visible: boolean;
  onClose: () => void;
  value: Filters;
  onApply: (f: Filters) => void;
  meta?: Meta;
}) {
  const styles = useStyles();
  const { t, pick, lang } = useLang();
  const [f, setF] = useState<Filters>(value);

  useEffect(() => {
    if (visible) setF(value);
  }, [visible, value]);

  const toggle = (arr: string[], v: string) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);
  const segments = meta?.categories.filter((c) => c.kind === "segment") ?? [];
  const types = (meta?.property_types ?? []).filter((pt) => !f.segment || f.segment === "new-projects" || pt.segment === f.segment);
  const localities = (meta?.localities ?? []).filter((l) => !f.zone || l.zone_id === meta?.zones.find((z) => z.slug === f.zone)?.id);

  return (
    <Sheet
      visible={visible}
      onClose={onClose}
      title={t("filters")}
      testID="filter-sheet"
      footer={
        <View style={styles.footerRow}>
          <Button label={t("reset")} variant="outline" onPress={() => setF({ ...DEFAULT_FILTERS, purpose: f.purpose })} testID="filter-reset-btn" style={{ flex: 1 }} />
          <Button label={t("applyFilters")} onPress={() => onApply(f)} testID="filter-apply-btn" style={{ flex: 2 }} />
        </View>
      }
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Section title={t("buy") + " / " + t("rent")}>
          <View style={styles.wrapRow}>
            {(["buy", "rent"] as const).map((p) => (
              <Chip key={p} label={t(p)} selected={f.purpose === p} onPress={() => setF({ ...f, purpose: p, budget: undefined })} testID={`filter-purpose-${p}`} />
            ))}
          </View>
        </Section>
        <Section title={t("category")}>
          <View style={styles.wrapRow}>
            {segments.map((s) => (
              <Chip key={s.slug} label={pick(s, "name")} selected={f.segment === s.slug} onPress={() => setF({ ...f, segment: f.segment === s.slug ? undefined : s.slug, type: undefined })} testID={`filter-segment-${s.slug}`} />
            ))}
          </View>
        </Section>
        <Section title={t("propertyType")}>
          <View style={styles.wrapRow}>
            {types.map((pt) => (
              <Chip key={pt.slug} label={pick(pt, "name")} selected={f.type === pt.slug} onPress={() => setF({ ...f, type: f.type === pt.slug ? undefined : pt.slug })} testID={`filter-type-${pt.slug}`} />
            ))}
          </View>
        </Section>
        <Section title={t("budget")}>
          <View style={styles.wrapRow}>
            {BUDGETS[f.purpose].map((b) => (
              <Chip key={b.key} label={lang === "hi" ? b.hi : b.en} selected={f.budget === b.key} onPress={() => setF({ ...f, budget: f.budget === b.key ? undefined : b.key })} testID={`filter-budget-${b.key}`} />
            ))}
          </View>
        </Section>
        <Section title={t("bhk")}>
          <View style={styles.wrapRow}>
            {BHKS.map((b) => (
              <Chip key={b} label={`${b} BHK`} selected={f.bhk.includes(b)} onPress={() => setF({ ...f, bhk: toggle(f.bhk, b) })} testID={`filter-bhk-${b}`} />
            ))}
          </View>
        </Section>
        <Section title={t("locality")}>
          <View style={styles.wrapRow}>
            {localities.map((l) => (
              <Chip key={l.slug} label={pick(l, "name")} selected={f.locality.includes(l.slug)} onPress={() => setF({ ...f, locality: toggle(f.locality, l.slug) })} testID={`filter-locality-${l.slug}`} />
            ))}
          </View>
        </Section>
        <Section title={t("sortBy")}>
          <View style={styles.wrapRow}>
            {([["newest", "newest"], ["price_asc", "priceLow"], ["price_desc", "priceHigh"]] as const).map(([k, label]) => (
              <Chip key={k} label={t(label)} selected={f.sort === k} onPress={() => setF({ ...f, sort: k })} testID={`filter-sort-${k}`} />
            ))}
          </View>
        </Section>
      </ScrollView>
    </Sheet>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  const styles = useStyles();
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  content: { paddingHorizontal: 16, paddingBottom: 16 },
  section: { marginBottom: 24 },
  sectionTitle: { fontFamily: fonts.textSemi, fontSize: 14, color: c.onSurfaceSecondary, marginBottom: 12, letterSpacing: 0.3 },
  wrapRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  footerRow: { flexDirection: "row", gap: 12 },
}));
