import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { adminSections, type AdminSection } from "@/lib/admin-resources";
import { adminRecords } from "@/lib/admin-server";
import { resourceStatuses } from "@/lib/admin-routes";
import { Gallery } from "@/components/properties/gallery";
import { OperationEditor, LocalityActions, EnquiryDetail, PaymentDetails } from "@/components/admin/operation-editor";
import { ModerationControl } from "@/components/admin/moderation-control";

export const metadata: Metadata = { title: "Administration", robots: { index: false, follow: false } };
export default async function AdminResourcePage({ params, searchParams }: { params: Promise<{ section: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { section: raw } = await params;
  if (!Object.hasOwn(adminSections, raw)) notFound();
  const section = raw as AdminSection;
  const config = adminSections[section];
  const query = await searchParams;
  const statuses = resourceStatuses(section);
  const status = typeof query.status === "string" ? query.status : statuses[0] || "";
  const q = typeof query.q === "string" ? query.q.trim().slice(0, 100) : "";
  const page = query.page === undefined ? 1 : typeof query.page === "string" && /^[1-9]\d{0,5}$/.test(query.page) ? Number(query.page) : 0;
  const invalid = Object.keys(query).some(key => !["status", "q", "page"].includes(key)) || Object.values(query).some(Array.isArray) || !page || (query.status !== undefined && !statuses.includes(status));
  const result = invalid ? null : await adminRecords(section, status, q, page);
  const items = result?.kind === "ready" ? result.items.filter(item => result.serverPaged || [item.id, item.title, ...item.details.map(([, value]) => value)].some(value => value.toLowerCase().includes(q.toLowerCase()))) : [];
  const pages = Math.max(1, Math.ceil((result?.kind === "ready" && result.serverPaged ? result.total : items.length) / 20));
  const pageLink = (number: number) => `/admin/${section}?` + new URLSearchParams({ ...(status ? { status } : {}), ...(q ? { q } : {}), page: String(number) });
  return <main id="main" className="admin-main stack">
    <span className="eyebrow">OPERATIONS</span><h1>{config.title}</h1><p className="muted">{config.description}</p>
    {invalid ? <p className="notice error" role="alert">Invalid filters. <Link href={`/admin/${section}`}>Reset this view</Link>.</p> : result?.kind === "unsupported" ? <p className="notice" role="status">This module is unavailable until its backend capability and business controls are approved.</p> : result?.kind !== "ready" ? <div className="notice" role="status"><p>{result?.kind === "signed-out" || result?.kind === "denied" ? "Administrator access is required. No records have been loaded." : "Records could not be loaded. No sample data is shown."}</p><Link href={`/admin/${section}`}>Retry</Link></div> : <>
      <form className="panel stack" method="get"><div className="form-row">
        {statuses.length > 0 && <label>Status<select name="status" defaultValue={status}>{statuses.map(value => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select></label>}
        <label>Search records<input name="q" maxLength={100} defaultValue={q} type="search" /></label>
      </div><button className="button" type="submit">Apply filters</button><Link href={`/admin/${section}`}>Clear filters</Link></form>
      <OperationEditor section={section} />
      <p className="small muted">{result.serverPaged ? result.total : items.length} matching records{result.serverPaged ? "" : " in the returned configuration batch"}.</p>
      {!items.length || page > pages ? <p className="notice" role="status">No matching records on this page.</p> : (result.serverPaged ? items : items.slice((page - 1) * 20, page * 20)).map(item => <article className="panel stack" key={item.id} style={{ overflowWrap: "anywhere", minWidth: 0 }}>
        <h2>{item.title}</h2>{section === "properties" && <Gallery images={item.images} title={item.title} />}<p className="small muted">{item.id}{item.status ? ` · ${item.status.replaceAll("_", " ")}` : ""}</p>
        <dl className="property-facts">{item.details.map(([label, value]) => <div key={label}><dt>{label}</dt><dd style={{ whiteSpace: "pre-wrap", maxWidth: "100%" }}>{value}</dd></div>)}</dl>
        {item.documents.length > 0 && <div className="stack"><h3>Private verification documents</h3>{item.documents.map(doc => <a key={doc.id} href={`/api/files/${doc.id}`} target="_blank" rel="noopener noreferrer">Open {doc.name}</a>)}<p className="small muted">Opening another person’s private document is authorized and recorded by the backend.</p></div>}
        {section === "enquiries" && <EnquiryDetail id={item.id} />}
        {section === "payments" && <PaymentDetails id={item.id} />}
        <OperationEditor section={section} item={item} />
        {section === "locations" && <LocalityActions item={item} />}
        {(section === "properties" || section === "brokers") && <ModerationControl key={item.id + item.status} kind={section === "properties" ? "listings" : "brokers"} id={item.id} status={item.status} self={item.ownerId === result.viewerId} />}
      </article>)}
      <nav className="pagination" aria-label="Record pages">{page > 1 && <Link href={pageLink(page - 1)}>Previous</Link>}<span>Page {page} of {pages}</span>{page < pages && <Link href={pageLink(page + 1)}>Next</Link>}</nav>
    </>}
  </main>;
}
