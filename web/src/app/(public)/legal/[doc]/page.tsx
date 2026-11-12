import { notFound } from "next/navigation";
import { readConfig } from "@/lib/config";
import { backendHeaders } from "@/lib/backend-headers";
import { isRecord } from "@/lib/contracts";
export const dynamic = "force-dynamic";
export default async function LegalPage({ params }: { params: Promise<{ doc: string }> }) {
  const { doc } = await params;
  if (!["privacy", "terms"].includes(doc)) notFound();
  let content: { title: string; body: string; version: string } | null = null;
  try {
    const config = readConfig(process.env);
    const response = await fetch(`${config.backendOrigin}/api/legal/${doc}.json`, { headers: backendHeaders(config), credentials: "omit", cache: "no-store", redirect: "error", signal: AbortSignal.timeout(10000) });
    const data: unknown = response.ok ? await response.json() : null;
    if (isRecord(data) && typeof data.title === "string" && typeof data.body === "string") content = { title: data.title, body: data.body, version: typeof data.version === "string" ? data.version : "" };
  } catch { /* Safe, recoverable content-unavailable state. No fabricated legal text. */ }
  return <main id="main" className="container legal section"><span className="eyebrow">LANDVILLA POLICIES</span><h1>{content?.title || (doc === "privacy" ? "Privacy policy" : "Terms of use")}</h1>{content ? <><p className="muted">Version {content.version || "not provided"} · supplied by the LANDVILLA backend</p><div className="legal-body">{content.body}</div></> : <div className="notice" role="status">The policy could not be loaded. Please refresh once the backend is available. Review the policy before accepting it.</div>}</main>;
}
