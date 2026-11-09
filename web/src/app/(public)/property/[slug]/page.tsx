import type { Metadata } from "next";
import Link from "next/link";
import { cache } from "react";
import { notFound, permanentRedirect } from "next/navigation";
import { getPublicApi } from "@/lib/public-api";
import { PublicApiError } from "@/lib/public-transport";
import { propertyId } from "@/lib/property-query";
import { propertyHref, priceLabel } from "@/lib/property-links";
import { Gallery } from "@/components/properties/gallery";
import { PropertyActions } from "@/components/properties/property-actions";

import { RelatedProperties } from "@/components/properties/related-properties";
import { ShareProperty } from "@/components/properties/share-property";
import { canonicalOrigin } from "@/lib/seo";
export const dynamic = "force-dynamic";
const load = cache(async (slug: string) => {
  let id: string;
  try { id = propertyId(slug.slice(slug.lastIndexOf("~") + 1)); } catch { notFound(); }
  try { return await getPublicApi().property(id); } catch (error) { if (error instanceof PublicApiError && error.status === 404) notFound(); throw error; }
});
export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const p = await load((await params).slug);
  return { title: `${p.is_demo ? "Fictional demo: " : ""}${p.title}`, description: `${p.is_demo ? "Fictional demonstration, not a marketplace offer. " : ""}${p.type.replaceAll("-", " ")} in ${p.locality?.name_en || "Ujjain"}, Ujjain. ${p.area_sqft} sq ft.`, robots: { index: false, follow: false }, alternates: canonicalOrigin(process.env) ? { canonical: canonicalOrigin(process.env)! + propertyHref(p) } : undefined, openGraph: { title: p.title, description: p.is_demo ? "Fictional demonstration, not a marketplace offer." : `${p.type} in Ujjain`, type: "website" } };
}
export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params; const p = await load(slug);
  if (`/property/${slug}` !== propertyHref(p)) permanentRedirect(propertyHref(p));
  return <main id="main" className="container section stack"><Link href="/properties">← Discover properties</Link>{p.is_demo && <p className="notice">Fictional demo listing — not a genuine marketplace offer.</p>}<span className="eyebrow">{p.purpose === "buy" ? "FOR SALE" : "FOR RENT"} · UJJAIN</span><h1>{p.title}</h1><p>{p.locality?.name_en || "Locality unavailable"} · {p.type.replaceAll("-", " ")}</p><Gallery images={p.images} title={p.title} /><section className="panel stack"><h2>{priceLabel(p.price)}{p.purpose === "rent" ? " / month" : ""}</h2><dl className="property-facts"><div><dt>Area</dt><dd>{p.area_sqft.toLocaleString("en-IN")} sq ft</dd></div>{p.bhk !== null && <div><dt>Bedrooms</dt><dd>{p.bhk}</dd></div>}{p.bathrooms !== null && <div><dt>Bathrooms</dt><dd>{p.bathrooms}</dd></div>}{p.furnishing && <div><dt>Furnishing</dt><dd>{p.furnishing.replaceAll("-", " ")}</dd></div>}{p.posted_as && <div><dt>Listed by</dt><dd>{p.posted_as}</dd></div>}</dl><h2>About this property</h2><p className="description">{p.description || "No description supplied."}</p>{p.amenities.length > 0 && <><h3>Amenities</h3><ul>{p.amenities.map(a => <li key={a}>{a.replaceAll("-", " ")}</li>)}</ul></>}<p className="small muted">Listing information is supplied by the lister. Moderation is not proof of legal title or ownership. Independently verify details before a decision.</p></section><ShareProperty /><PropertyActions id={p.id} demo={p.is_demo} /><RelatedProperties property={p} /></main>;
}
