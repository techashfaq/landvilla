import Link from "next/link";
import { notFound } from "next/navigation";
import { getPublicApi } from "@/lib/public-api";
import { canonicalOrigin } from "@/lib/seo";
export const dynamic = "force-dynamic";
export function generateMetadata() {
  const origin = canonicalOrigin(process.env);
  return { title: "Explore Ujjain localities", description: "Browse the LANDVILLA locality directory and find current property listings in Ujjain.", robots: { index: false, follow: false }, ...(origin ? { alternates: { canonical: origin + "/city/ujjain" } } : {}) };
}
export default async function CityPage({ params }: { params: Promise<{ city: string }> }) {
  if ((await params).city !== "ujjain") notFound();
  const meta = await (async () => { try { return await getPublicApi().meta(); } catch { return null; } })();
  return <main id="main" className="container section stack"><span className="eyebrow">MADHYA PRADESH</span><h1>Explore Ujjain.</h1><p>Choose a locality to view current listings. Directory entries do not imply that properties are available or verified.</p><Link className="button" href="/properties">Search all properties</Link>{!meta ? <div className="notice" role="alert">The locality directory is temporarily unavailable. <Link href="/city/ujjain">Retry</Link></div> : meta.localities.length === 0 ? <p role="status">No localities are available in the directory yet.</p> : <ul className="locality-directory">{meta.localities.map(place => <li key={place.id}><Link href={`/city/ujjain/${encodeURIComponent(place.slug)}`}>{place.name_en}</Link></li>)}</ul>}</main>;
}
