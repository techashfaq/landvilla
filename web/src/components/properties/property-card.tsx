import Link from "next/link";
import type { PublicProperty } from "@/lib/property-contracts";
import { propertyHref, priceLabel } from "@/lib/property-links";
import { PropertyImage } from "./property-image";
export function PropertyCard({ property: p }: { property: PublicProperty }) {
  return <article className="property-card"><Link href={propertyHref(p)} className="property-photo"><PropertyImage src={p.images[0]} alt={p.title} /></Link><div className="property-copy stack"><div className="badges">{p.is_demo && <span className="badge demo">Fictional demo listing</span>}{p.featured && <span className="badge">Featured</span>}<span className="badge">{p.purpose === "rent" ? "For rent" : "For sale"}</span></div><strong className="price">{priceLabel(p.price)}{p.purpose === "rent" && <small> / month</small>}</strong><h3><Link href={propertyHref(p)}>{p.title}</Link></h3><p>{p.locality?.name_en || "Locality unavailable"} · Ujjain</p><p className="small">{p.bhk ? `${p.bhk} BHK · ` : ""}{p.bathrooms ? `${p.bathrooms} bath · ` : ""}{p.area_sqft.toLocaleString("en-IN")} sq ft</p><p className="small muted">{p.type.replaceAll("-", " ")}{p.posted_as ? ` · ${p.posted_as === "owner" ? "Owner" : "Broker"} listing` : ""}</p></div></article>;
}
