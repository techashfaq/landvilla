import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";

import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import type { Lang } from "@/src/i18n";

export type Locality = { id: string; slug: string; name_en: string; name_hi: string; zone_id: string | null; parent_id: string | null; verification_status: string };
export type Zone = { id: string; slug: string; name_en: string; name_hi: string };
export type Lookup = { id: string; slug: string; name_en: string; name_hi: string; icon?: string; segment?: string; has_bhk?: boolean; kind?: string };
export type Meta = { city: any; zones: Zone[]; localities: Locality[]; categories: Lookup[]; property_types: Lookup[]; amenities: Lookup[] };

export type Property = {
  id: string;
  title_en: string;
  title_hi: string;
  description_en: string;
  description_hi: string;
  purpose: "buy" | "rent";
  segment: string;
  type: string;
  price: number;
  bhk: number | null;
  bathrooms: number | null;
  area_sqft: number | null;
  furnishing: string | null;
  amenities: string[];
  images: string[];
  is_demo: boolean;
  featured: boolean;
  verification_status: string;
  locality: Locality | null;
  zone: Zone | null;
  is_saved: boolean;
  created_at: string;
};

export function useMeta() {
  return useQuery({ queryKey: ["meta"], queryFn: () => api<Meta>("/meta"), staleTime: 5 * 60 * 1000 });
}

export function formatPrice(price: number, purpose: string, lang: Lang) {
  const hi = lang === "hi";
  let s: string;
  if (purpose === "rent" || price < 100000) {
    s = `₹${price.toLocaleString("en-IN")}`;
  } else if (price >= 10000000) {
    s = `₹${+(price / 10000000).toFixed(2)} ${hi ? "करोड़" : "Cr"}`;
  } else {
    s = `₹${+(price / 100000).toFixed(2)} ${hi ? "लाख" : "L"}`;
  }
  return purpose === "rent" ? `${s}${hi ? "/माह" : "/mo"}` : s;
}

export function useToggleSave() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const router = useRouter();
  const m = useMutation({
    mutationFn: (p: { id: string; saved: boolean }) =>
      api(`/saved/${p.id}`, { method: p.saved ? "DELETE" : "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["properties"] });
      qc.invalidateQueries({ queryKey: ["property"] });
      qc.invalidateQueries({ queryKey: ["saved"] });
    },
  });
  return (id: string, saved: boolean) => {
    if (!user) {
      router.push("/login");
      return;
    }
    m.mutate({ id, saved });
  };
}
