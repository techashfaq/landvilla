import React, { useEffect, useRef, useState } from "react";
import { Text, View } from "react-native";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";

type GoogleApi = { accounts: { id: { initialize: (options: { client_id: string; nonce: string; callback: (response: { credential: string }) => void }) => void; renderButton: (element: HTMLElement, options: { theme: string; size: string }) => void } } };
let sdk: Promise<void> | undefined;
function loadSdk() {
  return sdk ??= new Promise<void>((resolve, reject) => {
    if ((window as unknown as { google?: GoogleApi }).google) { resolve(); return; }
    const script = document.createElement("script"); script.src = "https://accounts.google.com/gsi/client"; script.async = true;
    script.onload = () => resolve(); script.onerror = () => { sdk = undefined; script.remove(); reject(new Error("Google sign-in is unavailable. Use email sign-in or try again later.")); };
    document.head.appendChild(script);
  });
}
export function IndependentGoogle({ link = false }: { link?: boolean } = {}) {
  const target = useRef<HTMLDivElement>(null); const { acceptSession } = useAuth(); const [error, setError] = useState("");
  const clientId = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID;
  useEffect(() => {
    if (!clientId) return;
    let active = true;
    loadSdk().then(async () => {
      const { nonce } = await api("/auth/browser/google-nonce", { method: "POST" });
      if (!active || !target.current) return;
      const google = (window as unknown as { google: GoogleApi }).google;
      google.accounts.id.initialize({ client_id: clientId, nonce, callback: response => {
        if (!active) return;
        if (!response.credential) { setError("Google sign-in was cancelled or did not return a credential."); return; }
        setError("");
        api(link ? "/auth/google/link" : "/auth/google", { method: "POST", body: { id_token: response.credential } })
          .then(async result => { if (active) { if (link) setError("Google account linked."); else await acceptSession(result); } })
          .catch(e => { if (active) setError(e.message); });
      } });
      google.accounts.id.renderButton(target.current, { theme: "outline", size: "large" });
    }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [clientId, acceptSession, link]);
  if (!clientId) return null;
  return <View style={{ marginVertical: 12 }}><div ref={target} />{!!error && <Text accessibilityRole="alert">{error}</Text>}</View>;
}
