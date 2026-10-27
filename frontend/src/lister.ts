import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { Platform } from "react-native";

import { api } from "@/src/api";
import { useAuth } from "@/src/auth";

/** In-app purchase of Featured placement is only offered on web. Android/iOS store builds hide it until a store-compliant billing approach is approved. */
export const FEATURED_PURCHASE_ALLOWED = Platform.OS === "web";

export type BrokerInfo = { status: "pending" | "approved" | "rejected" | "suspended"; full_name: string; firm_name: string; rera_number: string; rera_status: string; admin_note: string | null } | null;
export type ListerInfo = { can_post_as_owner: boolean; can_post_as_broker: boolean; broker: BrokerInfo };

export function useLister() {
  const { user } = useAuth();
  return useQuery({ queryKey: ["lister", user?.user_id], queryFn: () => api<ListerInfo>("/me/lister"), enabled: !!user });
}

export const LISTING_STATUS: Record<string, { en: string; hi: string; kind: "verified" | "demo" | "featured" | "muted" }> = {
  pending_review: { en: "Under review", hi: "समीक्षा में", kind: "muted" },
  changes_requested: { en: "Changes requested", hi: "बदलाव ज़रूरी", kind: "demo" },
  active: { en: "Live", hi: "लाइव", kind: "verified" },
  rejected: { en: "Rejected", hi: "अस्वीकृत", kind: "demo" },
  sold_rented: { en: "Sold / Rented", hi: "बिक/किराए पर", kind: "muted" },
  expired: { en: "Expired", hi: "समाप्त", kind: "muted" },
};

export const LEAD_STATUS: Record<string, { en: string; hi: string }> = {
  new: { en: "New", hi: "नई" },
  contacted: { en: "Contacted", hi: "संपर्क किया" },
  follow_up: { en: "Follow-up", hi: "फ़ॉलो-अप" },
  closed: { en: "Closed", hi: "बंद" },
};

/** Redirects guests to login; returns true when the user is signed in. */
export function useRequireLogin() {
  const { user, loading } = useAuth();
  const router = useRouter();
  return { user, loading, goLogin: () => router.push("/login") };
}
