import { Ionicons } from "@react-native-vector-icons/ionicons";
import * as ImagePicker from "expo-image-picker";
import { Image } from "expo-image";
import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Linking, Platform, Pressable, Text, View } from "react-native";

import { API_BASE, fileUrl, authHeaders, getApiSessionVersion } from "@/src/api";
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
  const headers = await authHeaders();
  const session = getApiSessionVersion();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 60000);
  try {
    const res = await uploadForm(`${API_BASE}/uploads`, {
      headers, signal: controller.signal,
      fields: { kind },
      files: { file: { uri: asset.uri, name: asset.fileName || asset.name || "upload.jpg", mimeType: asset.mimeType || "image/jpeg" } },
    });
    if (!res.ok) throw new Error(res.status >= 500 ? "Upload unavailable. Please retry." : await readError(res));
    const data = await res.json();
    if (session !== getApiSessionVersion()) throw new Error("Session changed. Please retry.");
    if (!data || typeof data.id !== "string" || !/^[a-zA-Z0-9_-]{1,100}$/.test(data.id) || data.url !== `/api/files/${data.id}`) throw new Error("Invalid upload response. Please retry.");
    return data as { id: string; url: string; content_type: string };
  } finally { clearTimeout(timer); }

}

export function PhotoPicker({ photos, onChange, max = 10, disabled = false, onBusyChange }: { photos: Photo[]; onChange: (p: Photo[]) => void; max?: number; disabled?: boolean; onBusyChange?: (busy: boolean) => void }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { tx } = useLang();
  const toast = useToast();
  const locked = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const [failed, setFailed] = useState<ImagePicker.ImagePickerAsset[]>([]);
  const [busy, setBusy] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [progress, setProgress] = useState("");

  const pick = async (retry = false) => {
    if (locked.current || disabled || photos.length >= max) return;
    locked.current = true;
    setBusy(true);
    onBusyChange?.(true);
    const added: Photo[] = [];
    try {
      let assets = failed;
      if (!retry) {
        // Android's system Photo Picker does not need media-library permission.
        const perm = Platform.OS === "android" ? { granted: true } : await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!perm.granted) { setBlocked(true); return; }
        setBlocked(false);
        const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], allowsMultipleSelection: true, selectionLimit: max - photos.length, quality: 0.7 });
        if (result.canceled) return;
        assets = result.assets;
      }
      const selected = assets.slice(0, max - photos.length);
      const failures: ImagePicker.ImagePickerAsset[] = [];
      for (let i = 0; i < selected.length; i++) {
        if (!mounted.current) return;
        setProgress(`Uploading ${i + 1} of ${selected.length}`);
        try {
          const up = await uploadFile(selected[i], "property_photo");
          added.push({ id: up.id, url: up.url });
        } catch {
          failures.push(selected[i]);
        }
      }
      if (mounted.current) {
        setFailed(failures);
        if (failures.length) toast.show(`${failures.length} photo(s) failed to upload. Retry or remove them below.`, "error");
      }
    } catch {
      if (mounted.current) toast.show("Could not open photos. Please try again.", "error");
    } finally {
      locked.current = false;
      if (mounted.current) {
        if (added.length) onChange([...photos, ...added]);
        setBusy(false);
        setProgress("");
        onBusyChange?.(false);
      }
    }
  };

  return (
    <View>
      {!!progress && <Text accessibilityLiveRegion="polite">{progress}</Text>}
      <Text style={styles.hint}>{tx("Add up to 10 clear photos. First photo is the cover. Use photos of this property only.", "10 तक साफ़ फ़ोटो जोड़ें। पहली फ़ोटो कवर होगी। केवल इसी प्रॉपर्टी की फ़ोटो लगाएँ।")}</Text>
      <View style={styles.grid}>
        {photos.map((p, i) => (
          <View key={p.id} style={styles.tile} testID={`photo-tile-${i}`}>
            <Image source={{ uri: fileUrl(p.url) }} style={styles.img} contentFit="cover" />
            {i === 0 && <Text style={styles.cover}>{tx("Cover", "कवर")}</Text>}
            {i > 0 && <Pressable disabled={busy || disabled} accessibilityLabel="Move photo earlier" style={{ position: "absolute", left: 4, top: 4, backgroundColor: "white", padding: 6 }} onPress={() => { const next = [...photos]; [next[i - 1], next[i]] = [next[i], next[i - 1]]; onChange(next); }}><Text>←</Text></Pressable>}
            <Pressable disabled={busy || disabled} accessibilityLabel="Remove photo" testID={`photo-remove-${i}`} hitSlop={6} style={styles.remove} onPress={() => onChange(photos.filter((x) => x.id !== p.id))}>
              <Ionicons name="close" size={16} color={colors.onSurfaceInverse} />
            </Pressable>
          </View>
        ))}
        {photos.length < max && (
          <Pressable testID="add-photo-btn" style={[styles.tile, styles.add]} onPress={() => pick()} disabled={busy || disabled || failed.length > 0}>
            {busy ? <ActivityIndicator color={colors.brandPrimary} /> : <Ionicons name="camera-outline" size={28} color={colors.brandPrimary} />}
            <Text style={styles.addText}>{tx("Add photos", "फ़ोटो जोड़ें")}</Text>
          </Pressable>
        )}
      </View>
      {failed.length > 0 && <View style={{ gap: 8, marginTop: 12 }}>
        <Text accessibilityLiveRegion="polite">{failed.length} photos were not uploaded.</Text>
        <Pressable disabled={busy || disabled || photos.length >= max} onPress={() => pick(true)}><Text style={styles.settingsText}>Retry failed uploads</Text></Pressable>
        <Pressable disabled={busy || disabled} onPress={() => setFailed([])}><Text style={styles.settingsText}>Remove failed selections</Text></Pressable>
      </View>}
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
