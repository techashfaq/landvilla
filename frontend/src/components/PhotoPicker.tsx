import { Ionicons } from "@react-native-vector-icons/ionicons";
import * as ImagePicker from "expo-image-picker";
import { Image } from "expo-image";
import React, { useState } from "react";
import { ActivityIndicator, Linking, Platform, Pressable, Text, View } from "react-native";

import { API_BASE, fileUrl, getApiToken } from "@/src/api";
import { useToast } from "@/src/components/Toast";
import { useLang } from "@/src/i18n";
import { fonts, makeStyles, useTheme } from "@/src/theme";
import { uploadForm } from "@/src/utils/upload";

export type Photo = { id: string; url: string };

async function readError(res: Response) {
  try {
    const j = await res.json();
    return typeof j.detail === "string" ? j.detail : "Upload failed";
  } catch {
    return res.status === 402 ? "Storage quota exhausted" : "Upload failed";
  }
}

export async function uploadFile(asset: { uri: string; fileName?: string | null; name?: string; mimeType?: string | null }, kind: string) {
  const res = await uploadForm(`${API_BASE}/uploads`, {
    headers: { Authorization: `Bearer ${getApiToken()}` },
    fields: { kind },
    files: { file: { uri: asset.uri, name: asset.fileName || asset.name || "upload.jpg", mimeType: asset.mimeType || "image/jpeg" } },
  });
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()) as { id: string; url: string; content_type: string };
}

export function PhotoPicker({ photos, onChange, max = 10 }: { photos: Photo[]; onChange: (p: Photo[]) => void; max?: number }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { tx } = useLang();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [blocked, setBlocked] = useState(false);

  const pick = async () => {
    // Android uses the system Photo Picker, which needs no media permission.
    const perm = Platform.OS === "android" ? { granted: true, canAskAgain: true, status: "granted" } : await ImagePicker.getMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      if (!perm.canAskAgain && perm.status === "denied") {
        setBlocked(true);
        return;
      }
      const req = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!req.granted) {
        setBlocked(!req.canAskAgain);
        toast.show(tx("Photo access is needed to add property photos", "प्रॉपर्टी फ़ोटो जोड़ने के लिए फ़ोटो की अनुमति चाहिए"), "error");
        return;
      }
    }
    setBlocked(false);
    const r = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], allowsMultipleSelection: true, selectionLimit: max - photos.length, quality: 0.7 });
    if (r.canceled) return;
    setBusy(true);
    const added: Photo[] = [];
    try {
      for (const a of r.assets.slice(0, max - photos.length)) {
        const up = await uploadFile(a, "property_photo");
        added.push({ id: up.id, url: up.url });
      }
    } catch (e: any) {
      toast.show(e.message, "error");
    } finally {
      setBusy(false);
      onChange([...photos, ...added]);
    }
  };

  return (
    <View>
      <Text style={styles.hint}>{tx("Add up to 10 clear photos. First photo is the cover. Use photos of this property only.", "10 तक साफ़ फ़ोटो जोड़ें। पहली फ़ोटो कवर होगी। केवल इसी प्रॉपर्टी की फ़ोटो लगाएँ।")}</Text>
      <View style={styles.grid}>
        {photos.map((p, i) => (
          <View key={p.id} style={styles.tile} testID={`photo-tile-${i}`}>
            <Image source={{ uri: fileUrl(p.url) }} style={styles.img} contentFit="cover" />
            {i === 0 && <Text style={styles.cover}>{tx("Cover", "कवर")}</Text>}
            <Pressable testID={`photo-remove-${i}`} hitSlop={6} style={styles.remove} onPress={() => onChange(photos.filter((x) => x.id !== p.id))}>
              <Ionicons name="close" size={16} color={colors.onSurfaceInverse} />
            </Pressable>
          </View>
        ))}
        {photos.length < max && (
          <Pressable testID="add-photo-btn" style={[styles.tile, styles.add]} onPress={pick} disabled={busy}>
            {busy ? <ActivityIndicator color={colors.brandPrimary} /> : <Ionicons name="camera-outline" size={28} color={colors.brandPrimary} />}
            <Text style={styles.addText}>{tx("Add photos", "फ़ोटो जोड़ें")}</Text>
          </Pressable>
        )}
      </View>
      {blocked && (
        <Pressable testID="open-settings-btn" onPress={() => Linking.openSettings()} style={styles.settings}>
          <Ionicons name="settings-outline" size={18} color={colors.brandPrimary} />
          <Text style={styles.settingsText}>{tx("Photo access is off. Open Settings to allow it.", "फ़ोटो अनुमति बंद है। अनुमति देने के लिए सेटिंग्स खोलें।")}</Text>
        </Pressable>
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  hint: { fontFamily: fonts.text, fontSize: 13, color: c.muted, marginBottom: 12, lineHeight: 18 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  tile: { width: 100, height: 100, borderRadius: 12, overflow: "hidden", backgroundColor: c.surfaceTertiary },
  img: { width: "100%", height: "100%" },
  cover: { position: "absolute", left: 6, bottom: 6, backgroundColor: c.brandPrimary, color: c.onBrandPrimary, fontFamily: fonts.textSemi, fontSize: 11, paddingHorizontal: 6, borderRadius: 4 },
  remove: { position: "absolute", top: 4, right: 4, width: 26, height: 26, borderRadius: 13, backgroundColor: "rgba(28,25,23,0.7)", alignItems: "center", justifyContent: "center" },
  add: { borderWidth: 1.5, borderStyle: "dashed", borderColor: c.brandPrimary, alignItems: "center", justifyContent: "center", gap: 4, backgroundColor: c.brandTertiary },
  addText: { fontFamily: fonts.textMedium, fontSize: 12, color: c.onBrandTertiary },
  settings: { flexDirection: "row", gap: 8, alignItems: "center", marginTop: 12, padding: 12, borderRadius: 12, borderWidth: 1, borderColor: c.border },
  settingsText: { flex: 1, fontFamily: fonts.textMedium, fontSize: 13, color: c.brandPrimary },
}));
