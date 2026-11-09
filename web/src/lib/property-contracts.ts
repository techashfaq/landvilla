import { isRecord } from "./contracts.ts";
import { propertyId } from "./property-query.ts";

function text(value: unknown, max = 200): string {
  if (typeof value !== "string" || value.length > max) throw new Error("Invalid public property response.");
  return value;
}
function number(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) throw new Error("Invalid public property response.");
  return value;
}
function optionalNumber(value: unknown) { return value == null ? null : number(value); }
export type Place = { id: string; slug: string; name_en: string };
export function parsePlace(value: unknown): Place {
  if (!isRecord(value)) throw new Error("Invalid location response.");
  return { id: propertyId(text(value.id)), slug: propertyId(text(value.slug)), name_en: text(value.name_en) };
}
/** No arbitrary remote image proxying or private credential-bearing image URLs. */
export function publicImage(value: unknown): string | null {
  if (typeof value !== "string") return null;
  if (/^\/api\/files\/[a-zA-Z0-9_-]{1,100}$/.test(value)) return value;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.hostname !== "images.unsplash.com" || url.port || url.username || url.password || url.hash) return null;
    if ([...url.searchParams.keys()].some(key => !["w", "h", "q", "fit", "crop", "cs", "auto", "fm", "ixid", "ixlib"].includes(key))) return null;
    return url.href;
  } catch { return null; }
}
export type PublicProperty = {
  id: string; title: string; description: string; purpose: "buy" | "rent";
  segment: string; type: string; price: number; area_sqft: number;
  bhk: number | null; bathrooms: number | null; furnishing: string | null;
  amenities: string[]; images: string[]; locality: Place | null; zone: Place | null;
  is_demo: boolean; featured: boolean; posted_as: "owner" | "broker" | null;
};
export function parseProperty(value: unknown, now = Date.now()): PublicProperty {
  if (!isRecord(value) || !["buy", "rent"].includes(String(value.purpose))) throw new Error("Invalid public property response.");
  if (value.is_demo !== undefined && typeof value.is_demo !== "boolean") throw new Error("Invalid demo designation.");
  const until = typeof value.featured_until === "string" ? Date.parse(value.featured_until) : NaN;
  // No spread of backend fields: account IDs, contact details and internal documents stay out.
  return {
    id: propertyId(text(value.id)), title: text(value.title_en), description: text(value.description_en ?? "", 10000),
    purpose: value.purpose as "buy" | "rent", segment: text(value.segment), type: text(value.type),
    price: number(value.price), area_sqft: number(value.area_sqft), bhk: optionalNumber(value.bhk), bathrooms: optionalNumber(value.bathrooms),
    furnishing: value.furnishing == null ? null : text(value.furnishing),
    amenities: Array.isArray(value.amenities) ? value.amenities.slice(0, 100).map(v => text(v, 100)) : [],
    images: Array.isArray(value.images) ? value.images.slice(0, 10).map(publicImage).filter((v): v is string => v !== null) : [],
    locality: value.locality == null ? null : parsePlace(value.locality), zone: value.zone == null ? null : parsePlace(value.zone),
    is_demo: value.is_demo === true, featured: value.featured === true && Number.isFinite(until) && until > now,
    posted_as: value.posted_by_role === "owner" || value.posted_by_role === "broker" ? value.posted_by_role : null,
  };
}
export function parsePropertyPage(value: unknown) {
  if (!isRecord(value) || !Array.isArray(value.items) || value.items.length > 50) throw new Error("Invalid property results.");
  const total = number(value.total), page = number(value.page), limit = number(value.limit);
  if (![total, page, limit].every(Number.isSafeInteger) || page < 1 || limit < 1 || limit > 50 || value.items.length > limit || total < value.items.length) throw new Error("Invalid property pagination.");
  return { items: value.items.map(item => parseProperty(item)), total, page, limit };
}
export type Taxonomy = { slug: string; name_en: string; kind: string | null; segment: string | null };
function taxonomy(value: unknown): Taxonomy {
  if (!isRecord(value)) throw new Error("Invalid taxonomy.");
  return { slug: propertyId(text(value.slug)), name_en: text(value.name_en), kind: typeof value.kind === "string" ? text(value.kind) : null, segment: typeof value.segment === "string" ? text(value.segment) : null };
}
export function parseMeta(value: unknown) {
  if (!isRecord(value)) throw new Error("Invalid location response.");
  function list(key: string, max: number) {
    const rows = (value as Record<string, unknown>)[key];
    if (!Array.isArray(rows) || rows.length > max) throw new Error("Invalid location response.");
    return rows;
  }
  const city = parsePlace(value.city);
  if (city.slug !== "ujjain") throw new Error("This property search currently supports Ujjain only.");
  return { city, zones: list("zones", 100).map(parsePlace), localities: list("localities", 1000).filter(v => isRecord(v) && v.is_active === true).map(parsePlace), categories: list("categories", 100).map(taxonomy), property_types: list("property_types", 100).map(taxonomy), amenities: list("amenities", 100).map(taxonomy) };
}
export type PublicMeta = ReturnType<typeof parseMeta>;
export type PropertyPage = ReturnType<typeof parsePropertyPage>;
