"use client";
import { useEffect, useRef, useState } from "react";
import { useSession } from "@/components/session-provider";
import { isRecord } from "@/lib/contracts";
export function Conversation({ id, owner }: { id: string; owner: boolean }) {
  const { client, session } = useSession();
  const [result, setResult] = useState<{ key: string; data: Record<string, unknown> | null; error: string } | null>(null);

  const [revision, setRevision] = useState(0); const lock = useRef(false);
  const path = `/api/${owner ? "leads" : "enquiries"}/${id}`;
  const requestKey = JSON.stringify([path, revision, session?.user?.user_id, session?.csrf_token]);
  // Only render data belonging to this request, including before effects run.
  const current = result?.key === requestKey ? result : null;
  const data = current?.data ?? null; const error = current?.error ?? "";

  function setError(error: string) { setResult(previous => previous?.key === requestKey ? { ...previous, error } : previous); }

  useEffect(() => {
    let active = true;
    void client.account(path).then(data => {
      if (!isRecord(data)) throw new Error("Invalid conversation response.");
      if (active) setResult({ key: requestKey, data, error: "" });
    }).catch(() => { if (active) setResult({ key: requestKey, data: null, error: "This conversation is unavailable or you do not have access." }); });
    return () => { active = false; };
  }, [client, path, requestKey]);
  async function send(method: string, endpoint: string, body: unknown) { if (lock.current) return; lock.current = true; setError(""); try { await client.account(endpoint, method, body); setRevision(n => n + 1); } catch(e) { setError(e instanceof Error ? e.message : "Request failed."); } finally { lock.current = false; } }
  return <section className="stack"><h1>{owner ? "Lead conversation" : "Your enquiry"}</h1>{error && <p role="alert">{error}</p>}{!data && !error && <p role="status">Loading conversation…</p>}{data && <><p>Status: {String(data.status || "Unavailable")}</p>{data.phone && (!owner || data.share_phone_consent === true) ? <p>Contact: {String(data.phone)}</p> : <p>Phone contact is not shared here.</p>}<p>{String(data.message || "")}</p><div className="stack">{Array.isArray(data.messages) && data.messages.filter(isRecord).map((m, index) => <article className="panel" key={index}><strong>{m.from === "lister" ? "Lister" : "Buyer"}</strong><p className="description">{String(m.text || "")}</p></article>)}</div><form className="stack" onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); void send("POST", `/api/enquiries/${id}/messages`, { text: String(f.get("text") || "").trim() }); }}><label>Reply<textarea name="text" required minLength={1} maxLength={1000} /></label><button className="button">Send message</button></form>{owner && <form className="panel stack" onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); void send("PATCH", path, { status: f.get("status"), note: String(f.get("note") || "") }); }}><label>Lead status<select name="status" defaultValue={String(data.status || "new")}>{["new", "contacted", "follow_up", "closed"].map(s => <option key={s}>{s}</option>)}</select></label><label>Private follow-up note<textarea name="note" maxLength={1000} /></label><button className="button">Update lead</button></form>}</>}</section>;
}
