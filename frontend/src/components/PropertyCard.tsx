import { Ionicons } from "@react-native-vector-icons/ionicons";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import React from "react";
import { Pressable, Text, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";

import { Badge } from "@/src/components/ui";
import { formatPrice, Property, useToggleSave } from "@/src/data";
import { useLang } from "@/src/i18n";
import { fonts, makeStyles, useTheme } from "@/src/theme";

export function PropertyCard({ p, index = 0 }: { p: Property; index?: number }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { t, pick, lang } = useLang();
  const router = useRouter();
  const toggleSave = useToggleSave();

  return (
    <Animated.View entering={FadeInDown.delay(Math.min(index, 6) * 60).duration(350)}>
      <Pressable
        testID={`property-card-${p.id}`}
        onPress={() => router.push(`/property/${p.id}`)}
        style={({ pressed }) => [styles.card, pressed && { transform: [{ scale: 0.985 }] }]}
      >
        <View style={styles.imgWrap}>
          <Image source={{ uri: p.images[0] }} style={styles.img} contentFit="cover" transition={250} />
          <LinearGradient colors={["rgba(0,0,0,0.45)", "transparent"]} style={styles.scrim} />
          <View style={styles.badges}>
            {p.is_demo && <Badge label={t("demo")} kind="demo" testID={`demo-badge-${p.id}`} />}
            {p.verification_status === "verified" && <Badge label={t("verified")} kind="verified" />}
            {p.featured && <Badge label={t("featured")} kind="featured" />}
          </View>
          <Pressable
            testID={`save-btn-${p.id}`}
            hitSlop={8}
            onPress={() => toggleSave(p.id, p.is_saved)}
            style={styles.save}
          >
            <Ionicons name={p.is_saved ? "heart" : "heart-outline"} size={22} color={p.is_saved ? colors.brandPrimary : colors.onSurface} />
          </Pressable>
          <View style={styles.priceTag}>
            <Text style={styles.price} testID={`price-${p.id}`}>{formatPrice(p.price, p.purpose, lang)}</Text>
          </View>
        </View>
        <View style={styles.body}>
          <Text style={styles.title} numberOfLines={1}>{pick(p, "title")}</Text>
          <View style={styles.locRow}>
            <Ionicons name="location-outline" size={14} color={colors.muted} />
            <Text style={styles.loc} numberOfLines={1}>
              {pick(p.locality, "name")}
              {p.zone ? ` · ${pick(p.zone, "name")}` : ""}
            </Text>
          </View>
          <View style={styles.specs}>
            {p.bhk ? <Spec icon="bed-outline" text={`${p.bhk} ${t("bhk")}`} /> : null}
            {p.bathrooms ? <Spec icon="water-outline" text={`${p.bathrooms} ${t("baths")}`} /> : null}
            {p.area_sqft ? <Spec icon="resize-outline" text={`${p.area_sqft.toLocaleString("en-IN")} ${t("sqft")}`} /> : null}
          </View>
        </View>
      </Pressable>
    </Animated.View>
  );
}

function Spec({ icon, text }: { icon: any; text: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <View style={styles.spec}>
      <Ionicons name={icon} size={14} color={colors.onSurfaceTertiary} />
      <Text style={styles.specText}>{text}</Text>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  card: {
    backgroundColor: c.surface,
    borderRadius: 20,
    marginHorizontal: 16,
    marginBottom: 16,
    shadowColor: "#1C1917",
    shadowOpacity: 0.08,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
    elevation: 3,
  },
  imgWrap: { height: 200, borderTopLeftRadius: 20, borderTopRightRadius: 20, overflow: "hidden", backgroundColor: c.surfaceTertiary },
  img: { width: "100%", height: "100%" },
  scrim: { position: "absolute", top: 0, left: 0, right: 0, height: 80 },
  badges: { position: "absolute", top: 12, left: 12, flexDirection: "row", gap: 6 },
  save: { position: "absolute", top: 8, right: 8, width: 40, height: 40, borderRadius: 20, backgroundColor: c.surface, alignItems: "center", justifyContent: "center" },
  priceTag: { position: "absolute", bottom: 12, left: 12, backgroundColor: c.brandPrimary, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 999 },
  price: { color: c.onBrandPrimary, fontFamily: fonts.display, fontSize: 16 },
  body: { padding: 16, gap: 6 },
  title: { fontFamily: fonts.displaySemi, fontSize: 18, color: c.onSurface },
  locRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  loc: { fontFamily: fonts.text, fontSize: 14, color: c.muted, flex: 1 },
  specs: { flexDirection: "row", gap: 16, marginTop: 4 },
  spec: { flexDirection: "row", alignItems: "center", gap: 4 },
  specText: { fontFamily: fonts.textMedium, fontSize: 13, color: c.onSurfaceTertiary },
}));
