import Link from "next/link";
import { getPublicApi } from "@/lib/public-api";
import { propertyQuery } from "@/lib/property-query";
import { PropertyCard } from "./property-card";
import { SearchForm } from "./search-form";
export type SearchParams = Record<string, string | string[] | undefined>;
export async function Discovery({ params, purpose }: { params: SearchParams; purpose?: "buy" | "rent" }) {
  const raw = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) if (value !== undefined) for (const v of Array.isArray(value) ? value : [value]) raw.append(key, v);
  if (purpose && raw.has("purpose") && raw.get("purpose") !== purpose) return <main id="main" className="container section stack"><h1>Check your filters</h1><p>This page only supports {purpose} listings.</p><Link href="/properties">Open all property filters</Link></main>;
  if (purpose && !raw.has("purpose")) raw.set("purpose", purpose);
  let query: URLSearchParams;
  try { query = propertyQuery(raw); } catch { return <main id="main" className="container section stack"><h1>Check your filters</h1><p role="alert">An unsupported or invalid filter was supplied. No search was sent.</p><Link href="/properties">Clear filters and try again</Link></main>; }
  const data = await (async () => { try {
    const api = getPublicApi(); return await Promise.all([api.meta(), api.properties(query)]);
  } catch { return null; } })();
  if (!data) return <main id="main" className="container section stack"><h1>Property search is unavailable.</h1><p role="alert">We could not load current listings or locations. Please try again shortly.</p><Link href="/properties">Retry search</Link></main>;
  const [meta, results] = data;
    function pageHref(page: number) { const next = new URLSearchParams(query); next.set("page", String(page)); return `/properties?${next}`; }
    return <main id="main" className="container section stack"><span className="eyebrow">FIND YOUR PLACE</span><h1>{purpose === "buy" ? "Places to call your own." : purpose === "rent" ? "Room for your next chapter." : "Discover Ujjain."}</h1><SearchForm meta={meta} query={query} /><p role="status">{results.total} {results.total === 1 ? "property" : "properties"} · Page {results.page}</p>{results.items.some(p => p.is_demo) && <p className="notice">Listings marked “Fictional demo” are examples, not genuine marketplace offers.</p>}{results.items.length ? <div className="property-grid">{results.items.map(p => <PropertyCard key={p.id} property={p} />)}</div> : <div className="panel stack"><h2>No properties to show.</h2><p>Try another locality or a wider price range.</p><Link href="/properties">Clear your filters</Link></div>}<nav className="pagination" aria-label="Property pages">{results.page > 1 && <Link className="button secondary" href={pageHref(results.page - 1)}>Previous</Link>}{results.page * results.limit < results.total && <Link className="button" href={pageHref(results.page + 1)}>Next</Link>}</nav></main>;
}
