"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/components/session-provider";
import type { AdminRecord, AdminSection } from "@/lib/admin-resources";

export function OperationEditor({ section, item }: { section: AdminSection; item?: AdminRecord }) {
  const { client } = useSession(); const router = useRouter();
  const [open, setOpen] = useState(false); const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");
  const editable = item?.editable ?? {};
  const configurations: Partial<Record<AdminSection, string[]>> = {
    packages: ["name_en", "name_hi", "price_inr", "duration_days", "play_product_id", "benefits", "status", "is_active"],
    locations: ["name_en", "name_hi", "zone_id"], cms: ["kind", "title", "body", "status", "link"],
    cities: ["name_en", "name_hi", "slug"], zones: ["name_en", "name_hi", "slug", "is_active"],
    users: ["action"], enquiries: ["status"], reports: ["action"], staff: ["user_id", "permissions", "enabled"],
  };
  const fields = configurations[section];
  if (!fields || (!item && ["users", "enquiries", "reports"].includes(section)) || (item && section === "cities")) return null;
  const options: Record<string, string[]> = { kind: ["home-banner", "faq", "support"], status: section === "cms" ? ["draft", "published"] : section === "packages" ? ["draft", "active", "inactive"] : ["new", "contacted", "follow_up", "closed"], action: section === "reports" ? ["dismiss", "remove_listing", "suspend_user"] : ["suspend", "reactivate"] };
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const data = new FormData(event.currentTarget); const body: Record<string, unknown> = {};
    for (const field of fields!) body[field] = ["is_active", "enabled"].includes(field) ? data.has(field) : ["price_inr", "duration_days"].includes(field) ? Number(data.get(field)) : String(data.get(field) ?? "").trim();
    const note = String(data.get("note") ?? "").trim();
    let path = `/api/admin/${({ packages: "featured-plans", locations: "localities" } as Record<string, string>)[section] ?? section}`;
    let method: "POST" | "PUT" | "PATCH" = "POST";
    if (section === "users") { path += `/${item!.id}/${body.action}`; delete body.action; body.note = note; }
    else if (section === "enquiries" || section === "reports") { path += `/${item!.id}/${section === "reports" ? "resolve" : "status"}`; body.note = note; }
    else if (section === "staff") { const id = String(body.user_id); if (!/^[a-zA-Z0-9_-]{1,100}$/.test(id)) { setMessage("Enter a valid account ID."); return; } path += `/${id}/permissions`; delete body.user_id; body.permissions = String(body.permissions).split(",").map(x => x.trim()).filter(Boolean); body.note = note; }
    else { if (item) { path += `/${item.id}`; method = section === "locations" ? "PATCH" : "PUT"; } if (["cms", "cities", "zones"].includes(section)) body.note = note; if (section === "locations" && !body.zone_id) body.zone_id = null; }
    setBusy(true); setMessage("");
    try { await client.adminOperation(path, method, body); setOpen(false); setMessage("Saved. Records refreshed."); router.refresh(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Save failed. Please retry."); }
    finally { setBusy(false); }
  }
  return <div className="stack">{!open ? <button className="button secondary" onClick={() => setOpen(true)}>{item ? "Manage record" : "Create / configure"}</button> : <form className="panel stack" onSubmit={save}>
    <h3>{item ? "Update " + item.title : "Create / configure " + section}</h3>
    {fields.map(field => <label key={field}>{field.replaceAll("_", " ")}{options[field] ? <select name={field} defaultValue={String(editable[field] ?? options[field]![0])}>{options[field]!.map(value => <option key={value}>{value}</option>)}</select> : field === "body" ? <textarea name={field} required maxLength={4000} defaultValue={String(editable[field] ?? "")} /> : <input name={field} type={["is_active", "enabled"].includes(field) ? "checkbox" : ["price_inr", "duration_days"].includes(field) ? "number" : "text"} defaultChecked={field === "enabled" ? true : Boolean(editable[field])} defaultValue={String(field === "user_id" ? item?.id ?? "" : editable[field] ?? "")} required={!["is_active", "enabled", "zone_id", "link", "permissions", "play_product_id"].includes(field)} min={1} maxLength={field === "permissions" ? 300 : 160} />}</label>)}
    <label>Reason<textarea name="note" required minLength={5} maxLength={section === "reports" ? 500 : 1000} /></label>
    <label><input type="checkbox" required /> I confirm these changes and any publication or access effects.</label>
    <div className="hero-actions"><button className="button" disabled={busy}>{busy ? "Saving…" : "Confirm save"}</button><button type="button" className="button secondary" disabled={busy} onClick={() => setOpen(false)}>Cancel</button></div>
  </form>}{message && <p role="status">{message}</p>}</div>;
}

export function LocalityActions({ item }: { item: AdminRecord }) {
  const { client } = useSession(); const router = useRouter();
  const [action, setAction] = useState(""); const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");
  return <div className="stack"><div className="hero-actions">{[item.editable.is_active ? "deactivate" : "activate", "verify"].map(value => <button key={value} className="button secondary" onClick={() => setAction(value)}>{value}</button>)}</div>{action && <form className="stack" onSubmit={async event => {
    event.preventDefault(); if (busy) return; const data = new FormData(event.currentTarget); setBusy(true);
    try { await client.adminOperation(`/api/admin/localities/${item.id}/${action}`, "POST", action === "verify" ? { source: String(data.get("source")) } : {}); setAction(""); setMessage("Locality updated."); router.refresh(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Save failed."); } finally { setBusy(false); }
  }}><p>Confirm {action} for {item.title}. Public locality availability may change.</p>{action === "verify" && <label>Verified source<input name="source" minLength={3} maxLength={300} required /></label>}<button className="button" disabled={busy}>Confirm {action}</button><button type="button" disabled={busy} onClick={() => setAction("")}>Cancel</button></form>}{message && <p role="status">{message}</p>}</div>;
}

export function EnquiryDetail({ id }: { id: string }) {
  const { client } = useSession();
  const [details, setDetails] = useState<[string, string][] | null>(null); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  return <div className="stack"><button className="button secondary" disabled={busy} onClick={async () => {
    if (details) { setDetails(null); return; } setBusy(true); setError("");
    try {
      const data = await client.adminDetail(`/api/admin/enquiries/${id}`);
      if (!data || typeof data !== "object") throw new Error("Details unavailable");
      const value = data as Record<string, unknown>;
      setDetails(["name", "status", "intent", "message", "phone", "phone_masked", "property_title", "property_id", "lister_user_id", "created_at"].filter(key => typeof value[key] === "string").map(key => [key.replaceAll("_", " "), String(value[key])]));
    } catch (error) { setError(error instanceof Error ? error.message : "Details unavailable"); } finally { setBusy(false); }
  }}>{busy ? "Loading…" : details ? "Close private details" : "View enquiry details (audited)"}</button>{details && <dl className="property-facts">{details.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl>}{error && <p role="alert">{error}</p>}</div>;
}

export function PaymentDetails({ id }: { id: string }) {
  const { client } = useSession();
  const [data, setData] = useState<Record<string, unknown> | null>(null); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  return <div className="stack"><button className="button secondary" disabled={busy} onClick={async () => { setBusy(true); try { setData(await client.adminDetail(`/api/admin/payments/${id}`) as Record<string, unknown>); } catch (e) { setMessage(e instanceof Error ? e.message : "Details unavailable"); } finally { setBusy(false); } }}>Payment and webhook details</button>{data && <><dl className="property-facts">{["status", "mode", "provider", "razorpay_order_id", "razorpay_payment_id", "featured_from", "featured_until", "refund_status", "refund_id"].filter(key => typeof data[key] === "string").map(key => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{String(data[key])}</dd></div>)}</dl><h3>Processed webhook deliveries</h3>{Array.isArray(data.events) && data.events.map((event: Record<string, unknown>, i: number) => <p key={i}>{String(event.event ?? "")} · {String(event.event_id ?? "")} · {String(event.processed_at ?? "")}</p>)}<p>Refund processing is disabled for this release.</p></>}{message && <p role="status">{message}</p>}</div>;
}
