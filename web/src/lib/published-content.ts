import "server-only";
import { readConfig } from "@/lib/config";
import { backendHeaders } from "@/lib/backend-headers";
export async function publishedContent(kind: "home-banner" | "faq" | "support") {
  try {
    const config = readConfig(process.env);
    const response = await fetch(`${config.backendOrigin}/api/content?kind=${kind}`, { headers: backendHeaders(config), credentials: "omit", cache: "no-store", redirect: "error", signal: AbortSignal.timeout(5000) });
    if (!response.ok) return [];
    const data: unknown = await response.json();
    if (!data || typeof data !== "object" || !("items" in data) || !Array.isArray(data.items)) return [];
    return data.items.filter((item): item is { id: string; title: string; body: string; link: string } => !!item && typeof item.id === "string" && typeof item.title === "string" && typeof item.body === "string" && ["", "/properties", "/buy", "/rent", "/contact", "/faq"].includes(item.link)).slice(0, 100);
  } catch { return []; }
}
