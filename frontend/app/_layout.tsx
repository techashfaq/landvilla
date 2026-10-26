import { QueryClientProvider } from "@tanstack/react-query";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { ActivityIndicator, LogBox, StyleSheet, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { KeyboardProvider } from "react-native-keyboard-controller";

import { AuthProvider } from "@/src/auth";
import { ErrorBoundary } from "@/src/components/error-boundary";
import { ToastProvider } from "@/src/components/Toast";
import { LanguageProvider } from "@/src/i18n";
import { queryClient } from "@/src/query-client";
import { useTheme } from "@/src/theme";

// Disable logbox errors etc so that users can see the app
// and agent works as expected.
LogBox.ignoreAllLogs(true);

export default function RootLayout() {
  const { colors } = useTheme();
  const [loaded] = useFonts({
    "Mukta-Bold": require("../assets/fonts/Mukta-Bold.ttf"),
    "Mukta-SemiBold": require("../assets/fonts/Mukta-SemiBold.ttf"),
    "Hind-Regular": require("../assets/fonts/Hind-Regular.ttf"),
    "Hind-Medium": require("../assets/fonts/Hind-Medium.ttf"),
    "Hind-SemiBold": require("../assets/fonts/Hind-SemiBold.ttf"),
  });

  return (
    <GestureHandlerRootView style={styles.root}>
      <ErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <KeyboardProvider>
            <LanguageProvider>
              <AuthProvider>
                <ToastProvider>
                  <StatusBar style="dark" />
                  {loaded ? (
                    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.surface } }}>
                      <Stack.Screen name="(tabs)" />
                      <Stack.Screen name="property/[id]" />
                      <Stack.Screen name="login" options={{ presentation: "modal" }} />
                      <Stack.Screen name="admin/localities" />
                    </Stack>
                  ) : (
                    <View style={[styles.root, styles.center, { backgroundColor: colors.surface }]}>
                      <ActivityIndicator color={colors.brandPrimary} />
                    </View>
                  )}
                </ToastProvider>
              </AuthProvider>
            </LanguageProvider>
          </KeyboardProvider>
        </QueryClientProvider>
      </ErrorBoundary>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  center: { alignItems: "center", justifyContent: "center" },
});
