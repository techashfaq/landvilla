import { isRecord } from "./contracts.ts";
import { parseProperty, parsePropertyPage } from "./property-contracts.ts";

/** Keep the public API field names while projecting the same fields as public pages. */
export function publicPropertyResponse(value: unknown) {
  const p = parseProperty(value);
  return {
    id: p.id, title_en: p.title, description_en: p.description, purpose: p.purpose,
    segment: p.segment, type: p.type, price: p.price, area_sqft: p.area_sqft,
    bhk: p.bhk, bathrooms: p.bathrooms, furnishing: p.furnishing,
    amenities: p.amenities, images: p.images, locality: p.locality, zone: p.zone,
    is_demo: p.is_demo, featured: p.featured,
    featured_until: p.featured && isRecord(value) ? value.featured_until : null,
    posted_by_role: p.posted_as,
  };
}
export function publicPropertiesResponse(value: unknown) {
  const page = parsePropertyPage(value);
  if (!isRecord(value) || !Array.isArray(value.items)) throw new Error("Invalid response");
  return { items: value.items.map(publicPropertyResponse), total: page.total, page: page.page, limit: page.limit };
}
