import type { PublicProperty } from "./property-contracts.ts";
export function propertyHref(property: Pick<PublicProperty, "id" | "title">) {
  const title = property.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 70) || "property";
  return `/property/${title}~${property.id}`;
}
export function priceLabel(price: number) { return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(price); }
