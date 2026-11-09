"use client";

import { createContext, useContext, useEffect, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { BrowserClient } from "@/lib/browser-client";

const Context = createContext<BrowserClient | null>(null);
export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new BrowserClient());
  const router = useRouter();
  useEffect(() => {
    const channel = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel("landvilla-web-session") : null;
    client.setSessionChangedHandler(() => { channel?.postMessage("changed"); router.refresh(); });
    if (channel) channel.onmessage = () => { client.invalidate(); router.refresh(); };
    // No eager bootstrap on public pages: it creates a backend pre-auth session.
    // Revalidate server-rendered access on focus, without invalidating an active
    // Google popup callback or OTP attempt. Backend CSRF rejects stale browser tabs.
    const focus = () => { router.refresh(); };
    window.addEventListener("focus", focus);
    return () => { channel?.close(); window.removeEventListener("focus", focus); client.setSessionChangedHandler(() => {}); };
  }, [client, router]);
  return <Context.Provider value={client}>{children}</Context.Provider>;
}
export function useSession() {
  const client = useContext(Context);
  if (!client) throw new Error("Session provider is required.");
  const state = useSyncExternalStore(client.subscribe, client.snapshot, client.snapshot);
  return { client, ...state };
}
