"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/components/session-provider";
import { moderationActions, moderationBody } from "@/lib/admin-routes";

const labels: Record<string, string> = { approve: "Approve", reject: "Reject", "request-changes": "Request changes", suspend: "Suspend", deactivate: "Deactivate", reactivate: "Return to review" };
export function ModerationControl({ kind, id, status, self }: { kind: "listings" | "brokers"; id: string; status: string; self: boolean }) {
  const { client } = useSession();
  const router = useRouter();
  const [action, setAction] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [saved, setSaved] = useState(false);
  const actions = moderationActions(kind, status, self);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy || !actions.includes(action)) return;
    setBusy(true); setMessage("");
    try {
      moderationBody(action, note);
      await client.admin(`/api/admin/${kind}/${id}/${action}`, note);
      setSaved(true); setMessage("Decision saved. Refreshing records…"); router.refresh();
    } catch (error) { setMessage(error instanceof Error ? error.message : "The decision could not be saved."); }
    finally { setBusy(false); }
  }
  if (self) return <p className="notice">Another administrator must review your own listing or application.</p>;
  if (!actions.length) return <p className="small muted">No moderation transition is available for this status.</p>;
  return <div className="stack">
    {saved ? <p role="status">{message}</p> : <>
      {!action ? <div className="hero-actions">{actions.map(value => <button className="button secondary" key={value} type="button" onClick={() => { setAction(value); setMessage(""); }}>{labels[value]}</button>)}</div> : <form className="stack" onSubmit={submit}>
        <h3>Confirm: {labels[action]}</h3>
        <p>{action === "approve" ? kind === "listings" ? "This publishes the property if the backend accepts the decision." : "This permits the broker to submit properties for review." : action === "suspend" ? kind === "brokers" ? "This suspends broker access and removes their active listings from public discovery." : "This removes the property from public discovery." : "This changes listing or application visibility. The review note is shared with the applicant."}</p>
        <label>Review note {action === "approve" ? "(optional)" : "(required)"}<textarea value={note} maxLength={1000} minLength={action === "approve" ? undefined : 5} required={action !== "approve"} onChange={event => setNote(event.target.value)} disabled={busy} /></label>
        <div className="hero-actions"><button className="button" disabled={busy}>{busy ? "Saving…" : `Confirm ${labels[action]?.toLowerCase()}`}</button><button className="button secondary" type="button" disabled={busy} onClick={() => { setAction(""); setNote(""); setMessage(""); }}>Cancel</button></div>
      </form>}
      {message && <p className="notice error" role="alert">{message}</p>}
    </>}
  </div>;
}
