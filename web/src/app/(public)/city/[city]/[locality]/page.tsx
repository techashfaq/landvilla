import { notFound } from "next/navigation";
import Link from "next/link";
import { getPublicApi } from "@/lib/public-api";
import { PropertyCard } from "@/components/properties/property-card";
export const dynamic = "force-dynamic";
export const metadata = { title: "Ujjain locality properties", robots: { index: false, follow: false } };
export default async function Page({ params }: { params: Promise<{ city: string; locality: string }> }) {
  const { city, locality } = await params;
  if (city !== "ujjain" || !/^[a-z0-9-]{1,100}$/.test(locality)) notFound();
  const api = getPublicApi(); const meta = await api.meta(); const place = meta.localities.find(p => p.slug === locality);
  if (!place) notFound();
  const result = await api.properties(new URLSearchParams({ locality: place.id, limit: "12" }));
  if (!result.total) notFound();
  return <main id="main" className="container section stack"><span className="eyebrow">UJJAIN / MADHYA PRADESH</span><h1>Properties in {place.name_en}</h1><p>{result.total} current results. Locality information comes from LANDVILLA’s location directory.</p>{result.items.some(p => p.is_demo) && <p className="notice">Fictional examples are labelled and are not genuine marketplace offers.</p>}<div className="property-grid">{result.items.map(p => <PropertyCard key={p.id} property={p} />)}</div><Link className="button" href={`/properties?locality=${encodeURIComponent(place.id)}`}>Explore all results and filters</Link></main>;
}
