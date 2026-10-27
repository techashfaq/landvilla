import { Ionicons } from "@react-native-vector-icons/ionicons";
import { useQueryClient } from "@tanstack/react-query";
import React, { useEffect, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";

import { api } from "@/src/api";
import { useToast } from "@/src/components/Toast";
import { useLang } from "@/src/i18n";
import { fonts, makeStyles, useTheme } from "@/src/theme";

export type Msg = { id: string; from: "buyer" | "lister"; text: string; at: string };

/** In-app message thread between buyer and lister. `me` is the viewer's side. */
export function Thread({ enquiryId, messages, me, queryKey, blocked = false }: { enquiryId: string; messages: Msg[]; me: "buyer" | "lister"; queryKey: any[]; blocked?: boolean }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { tx, lang } = useLang();
  const toast = useToast();
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [blockedMsg, setBlockedMsg] = useState("");
  useEffect(() => {
    if (!blocked) setBlockedMsg("");
  }, [blocked]);

  const send = async () => {
    if (!text.trim()) return;
    setSending(true);
    try {
      await api(`/enquiries/${enquiryId}/messages`, { method: "POST", body: { text: text.trim() } });
      setText("");
      qc.invalidateQueries({ queryKey });
    } catch (e: any) {
      if (e.status === 403) setBlockedMsg(e.message);
      else toast.show(e.message, "error");
    } finally {
      setSending(false);
    }
  };

  return (
    <View>
      <Text style={styles.title}>{tx("Messages", "संदेश")}</Text>
      {messages.length === 0 && <Text style={styles.empty}>{tx("No messages yet.", "अभी कोई संदेश नहीं।")}</Text>}
      {messages.map((m) => (
        <View key={m.id} style={[styles.bubble, m.from === me ? styles.mine : styles.theirs]} testID={`msg-${m.id}`}>
          <Text style={[styles.text, m.from === me && { color: colors.onBrandPrimary }]}>{m.text}</Text>
          <Text style={[styles.time, m.from === me && { color: colors.onBrandPrimary }]}>
            {new Date(m.at).toLocaleString(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
          </Text>
        </View>
      ))}
      {blockedMsg || blocked ? (
        <Text style={styles.empty} testID="thread-blocked-notice">{tx("Messaging is not available in this conversation.", "इस बातचीत में संदेश उपलब्ध नहीं है।")}</Text>
      ) : (
      <View style={styles.composer}>
        <TextInput testID="thread-input" value={text} onChangeText={setText} placeholder={tx("Write a message…", "संदेश लिखें…")} placeholderTextColor={colors.muted} style={styles.input} multiline maxLength={1000} />
        <Pressable testID="thread-send-btn" onPress={send} disabled={sending || !text.trim()} style={[styles.send, (!text.trim() || sending) && { opacity: 0.5 }]}>
          <Ionicons name="send" size={18} color={colors.onBrandPrimary} />
        </Pressable>
      </View>
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  title: { fontFamily: fonts.displaySemi, fontSize: 18, color: c.onSurface, marginBottom: 8 },
  empty: { fontFamily: fonts.text, fontSize: 14, color: c.muted, marginBottom: 8 },
  bubble: { maxWidth: "82%", padding: 10, borderRadius: 12, marginBottom: 8 },
  mine: { alignSelf: "flex-end", backgroundColor: c.brandPrimary, borderBottomRightRadius: 4 },
  theirs: { alignSelf: "flex-start", backgroundColor: c.surfaceTertiary, borderBottomLeftRadius: 4 },
  text: { fontFamily: fonts.text, fontSize: 15, color: c.onSurface, lineHeight: 21 },
  time: { fontFamily: fonts.text, fontSize: 11, color: c.muted, marginTop: 2, opacity: 0.85 },
  composer: { flexDirection: "row", gap: 8, alignItems: "flex-end", marginTop: 8 },
  input: { flex: 1, minHeight: 48, maxHeight: 120, borderRadius: 12, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, paddingHorizontal: 12, paddingTop: 12, fontFamily: fonts.text, fontSize: 15, color: c.onSurface },
  send: { width: 48, height: 48, borderRadius: 24, backgroundColor: c.brandPrimary, alignItems: "center", justifyContent: "center" },
}));
