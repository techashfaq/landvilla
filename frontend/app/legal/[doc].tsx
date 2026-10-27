import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import React from "react";
import { ActivityIndicator, Linking, ScrollView, Text } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, BACKEND } from "@/src/api";
import { Button, EmptyState, ScreenHeader } from "@/src/components/ui";
import { useLang } from "@/src/i18n";
import { fonts, makeStyles, useTheme } from "@/src/theme";

export default function LegalDoc() {
  const { doc } = useLocalSearchParams<{ doc: string }>();
  const insets = useSafeAreaInsets();
  const styles = useStyles();
  const { colors } = useTheme();
  const { tx } = useLang();
  const router = useRouter();
  const q = useQuery({ queryKey: ["legal", doc], queryFn: () => api<{ title: string; version: string; body: string }>(`/legal/${doc}.json`) });
  const back = () => (router.canGoBack() ? router.back() : router.replace("/profile"));
  return (
    <ScrollView style={styles.screen} contentContainerStyle={{ paddingBottom: insets.bottom + 24 }} stickyHeaderIndices={[0]}>
      <ScreenHeader title={q.data?.title ?? tx("Legal", "कानूनी")} onBack={back} topInset={insets.top} />
      {q.isLoading ? <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 40 }} /> : q.isError ? (
        <EmptyState icon="cloud-offline-outline" title={tx("Couldn't load. Try again.", "लोड नहीं हुआ। फिर कोशिश करें।")} cta={tx("Retry", "फिर कोशिश करें")} onPress={() => q.refetch()} testID="legal-error" />
      ) : (
        <>
          <Text style={styles.version} testID="legal-version">{tx("Version", "संस्करण")} {q.data?.version}</Text>
          <Text style={styles.body} testID="legal-body">{q.data?.body}</Text>
          {doc === "privacy" && (
            <Button label={tx("Open account deletion page", "खाता हटाने का पेज खोलें")} variant="outline" onPress={() => Linking.openURL(`${BACKEND}/api/legal/delete-account`)} testID="legal-delete-page-btn" style={{ margin: 16 }} />
          )}
        </>
      )}
    </ScrollView>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surface },
  version: { fontFamily: fonts.textMedium, fontSize: 13, color: c.muted, paddingHorizontal: 16, marginTop: 16 },
  body: { fontFamily: fonts.text, fontSize: 15, lineHeight: 23, color: c.onSurfaceSecondary, padding: 16 },
}));
