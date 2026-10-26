import { Ionicons } from "@react-native-vector-icons/ionicons";
import { Tabs } from "expo-router";
import { NativeTabs } from "expo-router/native-tabs";
import React from "react";
import { Platform } from "react-native";

import { useLang } from "@/src/i18n";
import { usesNativeTabs } from "@/src/navigation";
import { fonts, useTheme } from "@/src/theme";

export default function TabsLayout() {
  const { t } = useLang();
  const { colors } = useTheme();

  if (usesNativeTabs) {
    return (
      <NativeTabs tintColor={colors.brandPrimary}>
        <NativeTabs.Trigger name="index">
          <NativeTabs.Trigger.Icon sf="house.fill" />
          <NativeTabs.Trigger.Label>{t("home")}</NativeTabs.Trigger.Label>
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="saved">
          <NativeTabs.Trigger.Icon sf="heart.fill" />
          <NativeTabs.Trigger.Label>{t("saved")}</NativeTabs.Trigger.Label>
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="enquiries">
          <NativeTabs.Trigger.Icon sf="bubble.left.and.bubble.right.fill" />
          <NativeTabs.Trigger.Label>{t("enquiries")}</NativeTabs.Trigger.Label>
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="profile">
          <NativeTabs.Trigger.Icon sf="person.crop.circle.fill" />
          <NativeTabs.Trigger.Label>{t("profile")}</NativeTabs.Trigger.Label>
        </NativeTabs.Trigger>
      </NativeTabs>
    );
  }

  const icon = (on: any, off: any) => ({ color, focused }: { color: string; focused: boolean }) => (
    <Ionicons name={focused ? on : off} size={24} color={color} />
  );

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.brandPrimary,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.divider,
          ...(Platform.OS === "web" ? { height: 64 } : {}),
        },
        tabBarItemStyle: { alignSelf: "center" },
        tabBarLabelStyle: { fontFamily: fonts.textMedium, fontSize: 12 },
      }}
    >
      <Tabs.Screen name="index" options={{ title: t("home"), tabBarIcon: icon("home", "home-outline"), tabBarButtonTestID: "tab-home" } as any} />
      <Tabs.Screen name="saved" options={{ title: t("saved"), tabBarIcon: icon("heart", "heart-outline"), tabBarButtonTestID: "tab-saved" } as any} />
      <Tabs.Screen name="enquiries" options={{ title: t("enquiries"), tabBarIcon: icon("chatbubbles", "chatbubbles-outline"), tabBarButtonTestID: "tab-enquiries" } as any} />
      <Tabs.Screen name="profile" options={{ title: t("profile"), tabBarIcon: icon("person-circle", "person-circle-outline"), tabBarButtonTestID: "tab-profile" } as any} />
    </Tabs>
  );
}
