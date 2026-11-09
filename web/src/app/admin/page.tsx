import type { Metadata } from "next";
import { dashboardStats } from "@/lib/server-api";
export const metadata: Metadata = { title: "Admin overview", robots: { index: false, follow: false } };
export default async function AdminPage() {
  const stats = await dashboardStats();
  const metrics = stats ? [["Pending properties", stats.pending_listings], ["Pending brokers", stats.pending_brokers], ["Open reports", stats.open_reports], ["Paid orders", stats.paid_orders]] as const : null;
  return <main id="main" className="admin-main"><span className="eyebrow">WORKSPACE OVERVIEW</span><h1>A clearer view<br />of LANDVILLA.</h1><p className="muted">Read-only counts from the existing backend. No sample metrics or new administrative actions.</p>{metrics ? <div className="metric-grid">{metrics.map(([label, count]) => <article className="metric" key={label}><span>{label}</span><strong>{count.toLocaleString("en-IN")}</strong></article>)}</div> : <div className="notice" role="status">Dashboard counts are unavailable. No values are shown until the backend confirms administrator access and returns valid data.</div>}<section className="panel"><span className="eyebrow">FOUNDATION ONLY</span><h2>One workspace. Carefully connected.</h2><p>This shell connects to existing backend authorization. Moderation, staff permissions, CMS and payment management require a separately approved implementation phase.</p><p className="small muted">Paid orders are an order count, not revenue. No currency totals or business rules have been inferred.</p></section></main>;
}
