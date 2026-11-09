import Link from "next/link";
import { getPublicApi } from "@/lib/public-api";
import { SearchForm } from "./search-form";
import { PropertyCard } from "./property-card";
export async function HomeDiscovery() {
  const data = await (async () => { try {
    const api = getPublicApi();
    return await Promise.all([api.meta(), api.properties(new URLSearchParams("limit=6&sort=newest"))]);
  } catch { return null; } })();
  if (!data) return <section className="container section stack" id="discover"><h2>Explore Ujjain.</h2><p role="status">Current property information is temporarily unavailable.</p><Link className="button" href="/properties">Try property search</Link></section>;
  const [meta, results] = data;
    return <section className="container section stack" id="discover"><span className="eyebrow">EXPLORE UJJAIN</span><h2>Find a place that fits.</h2><SearchForm meta={meta} /><div className="section-heading"><h2>Current listings</h2><Link href="/properties">View all properties</Link></div>{results.items.some(p => p.is_demo) && <p className="notice">Fictional demo listings are labelled and are not genuine marketplace offers.</p>}{results.items.length ? <div className="property-grid">{results.items.map(p => <PropertyCard property={p} key={p.id} />)}</div> : <p className="panel">No properties are available right now. Please check again soon.</p>}</section>;
}
