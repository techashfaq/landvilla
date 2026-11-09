import type { PublicMeta } from "@/lib/property-contracts";
import { propertyQuery } from "@/lib/property-query";
export function SearchForm({ meta, query = new URLSearchParams(), action = "/properties" }: { meta: PublicMeta; query?: URLSearchParams; action?: string }) {
  query = propertyQuery(query);
  function retainedOption(key: string, known: string[]) {
    const value = query.get(key);
    return value && !known.includes(value) ? <option value={value}>Current filter: {value}</option> : null;
  }
  return <form key={query.toString()} action={action} className="search-form panel">{["page", "limit"].map(key => query.has(key) ? <input key={key} type="hidden" name={key} value={query.get(key)!} /> : null)}<div className="filter-grid">
    <label>Buy or rent<select name="purpose" defaultValue={query.get("purpose") || ""}><option value="">Buy & rent</option><option value="buy">Buy</option><option value="rent">Rent</option></select></label>
    <label>Search Ujjain<input name="q" maxLength={300} defaultValue={query.get("q") || ""} placeholder="Locality or keyword" /></label>
    <label>Localities (IDs or slugs, separated by commas)<input name="locality" list="landvilla-localities" maxLength={300} defaultValue={query.get("locality") || ""} aria-describedby="locality-help" /><datalist id="landvilla-localities">{meta.localities.flatMap(l => [<option key={l.id} value={l.id}>{l.name_en}</option>, <option key={l.id + "-slug"} value={l.slug}>{l.name_en}</option>])}</datalist><span id="locality-help" className="small">Choose or enter up to 10 locality IDs or slugs, separated by commas without spaces.</span></label>
    <label>Category<select name="segment" defaultValue={query.get("segment") || ""}><option value="">All categories</option>{retainedOption("segment", meta.categories.filter(c => c.kind === "segment").map(c => c.slug))}{meta.categories.filter(c => c.kind === "segment").map(c => <option key={c.slug} value={c.slug}>{c.name_en}</option>)}</select></label>
    <label>Zone<select name="zone" defaultValue={query.get("zone") || ""}><option value="">All zones</option>{retainedOption("zone", meta.zones.map(z => z.id))}{meta.zones.map(z => <option key={z.id} value={z.id}>{z.name_en}</option>)}</select></label><label>Property type<select name="type" defaultValue={query.get("type") || ""}><option value="">All types</option>{retainedOption("type", meta.property_types.map(t => t.slug))}{meta.property_types.map(t => <option key={t.slug} value={t.slug}>{t.name_en}</option>)}</select></label>
    <label>Minimum price (₹)<input name="min_price" type="number" min="0" step="1" defaultValue={query.get("min_price") || ""} /></label>
    <label>Maximum price (₹)<input name="max_price" type="number" min="0" step="1" defaultValue={query.get("max_price") || ""} /></label>
    <label>Bedrooms (comma-separated)<input name="bhk" list="landvilla-bhk" maxLength={300} defaultValue={query.get("bhk") || ""} aria-describedby="bhk-help" /><datalist id="landvilla-bhk">{[...Array.from({ length: 20 }, (_, i) => String(i + 1)), "4+"].map(v => <option key={v} value={v}>{v} BHK</option>)}</datalist><span id="bhk-help" className="small">Enter up to 10 values from 1–20 or 4+, for example 2,3,4+.</span></label>
    <label>Sort<select name="sort" defaultValue={query.get("sort") || ""}><option value="">Default order</option><option value="newest">Newest (featured first)</option><option value="price_asc">Price: low to high</option><option value="price_desc">Price: high to low</option></select></label>
  </div><div className="hero-actions"><button className="button" type="submit">Find properties</button><a className="text-link" href="/properties">Clear filters</a><span className="small muted">Ujjain · Prices in INR</span></div></form>;
}
