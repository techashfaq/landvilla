"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSession } from "@/components/session-provider";
import { isRecord } from "@/lib/contracts";
import { parseProperty } from "@/lib/property-contracts";
import { PropertyCard } from "@/components/properties/property-card";

export function AccountPanel({ kind }: { kind: "profile" | "saved" | "enquiries" | "listings" | "leads" | "broker" }) {
  const { client, session } = useSession();
  const [result, setResult] = useState<{ key: string; data: unknown; error: string } | null>(null);
  const [message, setMessage] = useState<{ key: string; text: string } | null>(null);
  const [revision, setRevision] = useState(0); const lock = useRef(false);
  const [page, setPage] = useState(1);
  const path = { profile: "/api/me/profile", saved: "/api/saved", enquiries: "/api/enquiries/me", listings: `/api/listings/mine?page=${page}&limit=20`, leads: "/api/leads", broker: "/api/me/lister" }[kind];
  const requestKey = JSON.stringify([path, revision, session?.user?.user_id, session?.csrf_token]);
  // Only render data belonging to this request, including before effects run.
  const current = result?.key === requestKey ? result : null;
  const data = current?.data ?? null; const error = current?.error ?? "";
  const loading = current === null; const notice = message?.key === requestKey ? message.text : "";
  function setError(error: string) { setResult(previous => previous?.key === requestKey ? { ...previous, error } : previous); }
  function setNotice(text: string, nextRevision = revision) { setMessage({ key: JSON.stringify([path, nextRevision, session?.user?.user_id, session?.csrf_token]), text }); }
  useEffect(() => {
    let active = true;
    void client.account(path).then(data => {

      if (active) setResult({ key: requestKey, data, error: "" });
    }).catch(() => { if (active) setResult({ key: requestKey, data: null, error: "Unable to load this account information. Please retry." }); });
    return () => { active = false; };
  }, [client, path, requestKey]);
  async function act(action: () => Promise<unknown>) {
    if (lock.current) return; lock.current = true; setError(""); setNotice("");
    try { await action(); setNotice("Saved successfully.", revision + 1); setRevision(n => n + 1); } catch (e) { setError(e instanceof Error ? e.message : "The operation failed."); } finally { lock.current = false; }
  }
  if (loading) return <p role="status">Loading your {kind}…</p>;
  const record = isRecord(data) ? data : {};
  const items = Array.isArray(record.items) ? record.items.filter(isRecord) : [];
  return <section className="stack"><h1>{kind === "profile" ? "Your profile" : `Your ${kind}`}</h1>{error && <p role="alert" className="notice error">{error}</p>}{notice && <p role="status">{notice}</p>}<button className="button secondary" onClick={() => { setError(""); setRevision(n => n + 1); }}>Refresh</button>
    {kind === "profile" && data !== null && <form className="panel stack" onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); void act(() => client.account(path, "PATCH", { first_name: String(f.get("first_name") || "").trim(), last_name: String(f.get("last_name") || "").trim(), preferred_location: String(f.get("preferred_location") || "").trim() })); }}><label>First name<input name="first_name" maxLength={60} required defaultValue={String(record.first_name || "")} /></label><label>Last name<input name="last_name" maxLength={60} required defaultValue={String(record.last_name || "")} /></label><label>Preferred location<input name="preferred_location" maxLength={120} defaultValue={String(record.preferred_location || "")} /></label><p>Email: {String(record.email || "Not supplied")} · {record.email_verified === true ? "Verified" : "Unverified"}</p><p>Mobile: {String(record.mobile || "Not supplied")} · {record.mobile_verified === true ? "Verified" : "Unverified"}</p><p>Profile: {record.profile_complete === true ? "Complete" : "Incomplete"}</p><p className="small muted">Contact details require separate verification and cannot be changed by this form.</p><button className="button">Save profile</button></form>}
    {kind === "saved" && <div className="property-grid">{items.map(item => { let p; try { p = parseProperty(item); } catch { return null; } return <div key={p.id} className="stack"><PropertyCard property={p} /><button className="button secondary" onClick={() => void act(() => client.account(`/api/saved/${p.id}`, "DELETE", {}))}>Remove saved property</button></div>; })}</div>}
    {["enquiries", "listings", "leads"].includes(kind) && items.map(item => <article className="panel stack" key={String(item.id)}><h2>{String(item.title_en || (isRecord(item.property) ? item.property.title_en : "") || "Property enquiry")}</h2><p>Status: {String(item.listing_status || item.status || "Unavailable")}</p>{kind === "listings" ? <><p>{String(item.lead_count || 0)} enquiries</p>{!["sold_rented", "expired"].includes(String(item.listing_status)) && <Link href={`/account/listings/${encodeURIComponent(String(item.id))}/edit`}>Edit and resubmit for review</Link>}</> : <Link href={`/account/${kind}/${encodeURIComponent(String(item.id))}`}>Open conversation</Link>}</article>)}
    {kind === "listings" && <><p className="small">Page {page}: {items.length} of {String(record.total ?? "unavailable")} listings. All submissions require backend moderation.</p><nav className="pagination" aria-label="Your listing pages"><button className="button secondary" disabled={page <= 1} onClick={() => setPage(n => n - 1)}>Previous</button><button className="button secondary" disabled={typeof record.total !== "number" || page * 20 >= record.total} onClick={() => setPage(n => n + 1)}>Next</button></nav><Link className="button" href="/account/listings/new">Submit a property</Link></>}
    {kind === "broker" && <div className="panel stack"><p>Broker status: {isRecord(record.broker) ? String(record.broker.status || "Unavailable") : "No application"}</p>{isRecord(record.broker) && record.broker.admin_note ? <p>Review note: {String(record.broker.admin_note)}</p> : null}<p>Broker approval remains an administrative decision.</p><Link href="/account/broker/apply">Broker application</Link></div>}
    {kind !== "profile" && kind !== "broker" && data !== null && !items.length && <p className="panel">Nothing to show yet.</p>}
  </section>;
}
