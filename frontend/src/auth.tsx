import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Platform } from "react-native";

import { api, setApiToken, setUnauthorizedHandler } from "@/src/api";
import { queryClient } from "@/src/query-client";
import { storage } from "@/src/utils/storage";

WebBrowser.maybeCompleteAuthSession();

export type User = { user_id: string; email: string; name?: string; picture?: string; role: "buyer" | "admin" };

type Ctx = {
  user: User | null;
  loading: boolean;
  signingIn: boolean;
  error: string | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<Ctx>({} as Ctx);
const TOKEN_KEY = "auth_token";
const AUTH_URL = "https://auth.emergentagent.com/";

function extractSessionId(url: string | null | undefined): string | null {
  if (!url) return null;
  const m = url.match(/[?#&]session_id=([^&#]+)/);
  return m ? decodeURIComponent(m[1]) : null;
}

async function saveToken(t: string | null) {
  if (Platform.OS === "web") {
    if (t) window.localStorage.setItem(TOKEN_KEY, t);
    else window.localStorage.removeItem(TOKEN_KEY);
  } else if (t) await storage.secureSet(TOKEN_KEY, t);
  else await storage.secureRemove(TOKEN_KEY);
}

async function readToken(): Promise<string | null> {
  if (Platform.OS === "web") return window.localStorage.getItem(TOKEN_KEY);
  return (await storage.secureGet(TOKEN_KEY, null)) as string | null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [signingIn, setSigningIn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sent = useRef(new Set<string>());

  const clear = useCallback(async () => {
    await saveToken(null);
    setApiToken(null);
    setUser(null);
    queryClient.removeQueries({ queryKey: ["saved"] });
    queryClient.removeQueries({ queryKey: ["enquiries"] });
    queryClient.invalidateQueries({ queryKey: ["properties"] });
  }, []);

  const exchange = useCallback(async (sessionId: string) => {
    if (sent.current.has(sessionId)) return false;
    sent.current.add(sessionId);
    setSigningIn(true);
    try {
      const res = await api<{ session_token: string; user: User }>("/auth/session", {
        method: "POST",
        body: { session_id: sessionId },
      });
      await saveToken(res.session_token);
      setApiToken(res.session_token);
      setUser(res.user);
      setError(null);
      queryClient.invalidateQueries();
      if (Platform.OS === "web") {
        const u = new URL(window.location.href);
        u.searchParams.delete("session_id");
        const hash = u.hash.replace(/^#/, "").split("&").filter((p) => p && !p.startsWith("session_id=")).join("&");
        u.hash = hash ? `#${hash}` : "";
        window.history.replaceState(window.history.state, "", u.toString());
      }
      return true;
    } catch {
      setError("Sign in failed. Please try again.");
      return false;
    } finally {
      setSigningIn(false);
    }
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      clear();
    });
    (async () => {
      try {
        const initial = Platform.OS === "web" ? window.location.href : await Linking.getInitialURL();
        const sid = extractSessionId(initial);
        if (sid && (await exchange(sid))) return;
        const token = await readToken();
        if (token) {
          setApiToken(token);
          try {
            setUser(await api<User>("/auth/me"));
          } catch (e: any) {
            // Only a real 401 signs the user out; offline/network errors keep the saved session.
            if (e?.status === 401) await clear();
          }
        }
      } finally {
        setLoading(false);
      }
    })();
    if (Platform.OS === "web") return;
    const sub = Linking.addEventListener("url", ({ url }) => {
      const sid = extractSessionId(url);
      if (sid) exchange(sid);
    });
    return () => sub.remove();
  }, [clear, exchange]);

  const login = useCallback(async () => {
    setError(null);
    if (Platform.OS === "web") {
      const redirect = window.location.origin + "/";
      window.location.href = `${AUTH_URL}?redirect=${encodeURIComponent(redirect)}`;
      return;
    }
    const redirect = Linking.createURL("");
    let captured: string | null = null;
    const sub = Linking.addEventListener("url", ({ url }) => {
      captured = url;
    });
    try {
      const result = await WebBrowser.openAuthSessionAsync(`${AUTH_URL}?redirect=${encodeURIComponent(redirect)}`, redirect);
      const url = (result.type === "success" ? result.url : null) || captured || (await Linking.getInitialURL());
      const sid = extractSessionId(url);
      if (sid) await exchange(sid);
    } finally {
      sub.remove();
    }
  }, [exchange]);

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {}
    await clear();
  }, [clear]);

  return (
    <AuthContext.Provider value={{ user, loading, signingIn, error, login, logout }}>{children}</AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
