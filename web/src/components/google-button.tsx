"use client";
import { useEffect, useRef, useState } from "react";
import { useSession } from "./session-provider";

type GoogleIdentity = { initialize(options: { client_id: string; nonce: string; callback: (response: { credential?: string }) => void }): void; renderButton(target: HTMLElement, options: { theme: string; size: string; text: string }): void; cancel(): void };
declare global { interface Window { google?: { accounts: { id: GoogleIdentity } } } }
let sdk: Promise<void> | undefined;
function loadGoogle() {
  if (window.google) return Promise.resolve();
  return sdk ??= new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client"; script.async = true;
    const timer = window.setTimeout(() => { sdk = undefined; script.remove(); reject(new Error("Google sign-in timed out. Use email or try again.")); }, 15000);
    script.onload = () => { clearTimeout(timer); resolve(); };
    script.onerror = () => { clearTimeout(timer); sdk = undefined; script.remove(); reject(new Error("Google sign-in is unavailable. Use email or try again.")); };
    document.head.appendChild(script);
  });
}
export function GoogleButton() {
  const { client } = useSession();
  const target = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID;
  useEffect(() => {
    if (!clientId) return;
    let active = true;
    let pending = false;
    void loadGoogle().then(async () => {
      if (!active) return;
      const nonce = await client.googleNonce();
      if (!active || !target.current || !window.google) return;
      window.google.accounts.id.initialize({ client_id: clientId, nonce, callback: response => {
        if (!active || pending) return;
        if (!response.credential) { setError("Google sign-in was cancelled or did not return a credential."); return; }
        pending = true;
        void client.google(response.credential).catch((e: unknown) => {
          if (active) setError(e instanceof Error ? e.message : "Google sign-in failed. Please retry.");
        }).finally(() => { pending = false; });
      } });
      target.current.replaceChildren();
      window.google.accounts.id.renderButton(target.current, { theme: "outline", size: "large", text: "continue_with" });
    }).catch((e: unknown) => { if (active) setError(e instanceof Error ? e.message : "Google sign-in could not start."); });
    return () => { active = false; window.google?.accounts.id.cancel(); };
  }, [client, clientId, attempt]);
  if (!clientId) return <p className="muted small">Google sign-in is not configured for this website. Email sign-in is available when the backend provider is ready.</p>;
  return <div className="google"><div ref={target} />{error && <><p role="alert">{error}</p><button type="button" className="button secondary" onClick={() => { setError(""); setAttempt(v => v + 1); }}>Restart Google sign-in</button></>}</div>;
}
