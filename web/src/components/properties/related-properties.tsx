import { getPublicApi } from "@/lib/public-api";
import type { PublicProperty } from "@/lib/property-contracts";
import { PropertyCard } from "./property-card";
export async function RelatedProperties({ property }: { property: PublicProperty }) {
  const results = await (async () => { try {
    const q = new URLSearchParams({ purpose: property.purpose, type: property.type, limit: "4" });
    if (property.locality) q.set("locality", property.locality.id);
    return await getPublicApi().properties(q);
  } catch { return null; } })();
  const items = results?.items.filter(p => p.id !== property.id).slice(0,3) || [];
  if (!items.length) return null;
  return <section className="stack"><h2>More properties with these filters</h2><p className="small muted">Same property type and purpose{property.locality ? " in this locality" : ""}. These are filtered results, not personalized recommendations.</p><div className="property-grid">{items.map(p => <PropertyCard key={p.id} property={p} />)}</div></section>;
}
