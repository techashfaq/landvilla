import { Image } from "expo-image";
import React, { useState } from "react";
import { StyleProp, Text, View, ViewStyle } from "react-native";
import { fileUrl } from "@/src/api";
import { useLang } from "@/src/i18n";

export function PropertyImage({ uri, identity, style }: { uri?: string; identity: string; style: StyleProp<ViewStyle> }) {
  const url = fileUrl(uri || "");
  const { tx } = useLang();
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  return <View style={[{ backgroundColor: "#E7E5E4", overflow: "hidden" }, style]}>
    {!url || failedUrl === url ? <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
      <Text accessibilityRole="text">{tx("Photo unavailable", "फ़ोटो उपलब्ध नहीं")}</Text>
    </View> : <Image source={{ uri: url }} recyclingKey={`${identity}:${url}`} style={{ width: "100%", height: "100%" }}
      contentFit="cover" cachePolicy="memory-disk" transition={150} accessibilityLabel="Property photo"
      onError={() => setFailedUrl(url)} />}
  </View>;
}
