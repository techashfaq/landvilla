import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React from "react";
import { ActivityIndicator, FlatList, RefreshControl, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { PropertyCard } from "@/src/components/PropertyCard";
import { EmptyState } from "@/src/components/ui";
import { Property } from "@/src/data";
import { useLang } from "@/src/i18n";
import { usesNativeTabs } from "@/src/navigation";
import { fonts, makeStyles, useTheme } from "@/src/theme";

export default function Saved() {
  const insets = useSafeAreaInsets();
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;
  const styles = useStyles();
  const { colors } = useTheme();
  const { t } = useLang();
  const { user } = useAuth();
  const router = useRouter();
  const q = useQuery({ queryKey: ["saved", user?.user_id], queryFn: () => api<{ items: Property[] }>("/saved"), enabled: !!user });

  return (
    <View style={styles.screen}>
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <Text style={styles.title} testID="saved-title">{t("saved")}</Text>
      </View>
      {!user ? (
        <EmptyState icon="heart-outline" title={t("loginRequired")} cta={t("signIn")} onPress={() => router.push("/login")} testID="saved-login" />
      ) : q.isLoading ? (
        <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 48 }} />
      ) : q.isError ? (
        <EmptyState icon="cloud-offline-outline" title={t("loadError")} cta={t("retry")} onPress={() => q.refetch()} testID="saved-error" />
      ) : (
        <FlatList
          data={q.data?.items ?? []}
          keyExtractor={(p) => p.id}
          renderItem={({ item, index }) => <PropertyCard p={item} index={index} />}
          contentContainerStyle={{ paddingTop: 16, paddingBottom: bottomChrome + 24 }}
          refreshControl={<RefreshControl refreshing={q.isRefetching} onRefresh={() => { q.refetch(); }} tintColor={colors.brandPrimary} />}
          ListEmptyComponent={<EmptyState icon="heart-outline" title={t("savedEmpty")} cta={t("explore")} onPress={() => router.navigate("/")} testID="saved-empty" />}
        />
      )}
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  screen: { flex: 1, backgroundColor: c.surfaceSecondary },
  header: { backgroundColor: c.surface, paddingHorizontal: 16, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: c.divider },
  title: { fontFamily: fonts.display, fontSize: 28, color: c.onSurface },
}));
