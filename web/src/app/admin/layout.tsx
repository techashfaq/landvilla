import Link from "next/link";
import { Brand } from "@/components/site-header";
import { adminAccess } from "@/lib/server-api";
export const dynamic = "force-dynamic";
export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const access = await adminAccess();
  if (access.kind !== "allowed") return <><header className="container admin-access-header"><Brand /></header><main id="main" className="container section"><span className="eyebrow">STAFF ACCESS</span><h1>{access.kind === "denied" ? "This account isn’t an administrator." : access.kind === "unavailable" ? "Unable to verify access." : "Sign in to continue."}</h1><p>{access.kind === "unavailable" ? "The backend or web configuration is unavailable. No dashboard data has been loaded." : "Administrator permissions are checked by the LANDVILLA backend. Account registration does not grant staff access."}</p><Link className="button" href="/login">Open account access</Link> <Link className="text-link" href="/">Back to website</Link></main></>;
  return <div className="admin-shell"><aside className="admin-sidebar"><Brand /><p className="eyebrow">WORKSPACE</p><nav aria-label="Admin navigation"><Link href="/admin" aria-current="page">Overview <span>↗</span></Link></nav><p className="sidebar-note">Property, broker and finance management are outside this foundation phase.</p><Link className="text-link" href="/">View website</Link></aside><div className="admin-content"><header className="admin-topbar"><span>LANDVILLA / ADMIN</span><Link href="/login">Account & sign out</Link></header>{children}</div></div>;
}
