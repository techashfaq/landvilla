import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Platform } from "react-native";

import { api, setApiToken, setUnauthorizedHandler, setBrowserSession, bootstrapBrowser } from "@/src/api";
import { queryClient } from "@/src/query-client";
import { storage } from "@/src/utils/storage";
import { SessionWrites } from "@/src/session-writes";

import { requestNativeGoogleToken, nativeGoogleError } from "@/src/native-google";

export type User = { user_id: string; email: string; name?: string; picture?: string; role: "buyer" | "admin" };

type Ctx = {
  user: User | null;
  loading: boolean;
  signingIn: boolean;
  error: string | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  acceptSession: (session: { session_token?: string; csrf_token?: string; user: User }) => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<Ctx>({} as Ctx);
const TOKEN_KEY = "auth_token";

function extractSessionId(url: string | null | undefined): string | null {
  if (!url) return null;
  const m = url.match(/[?#&]session_id=([^&#]+)/);
  return m ? decodeURIComponent(m[1]) : null;
}

async function saveToken(t: string | null) {
  if (Platform.OS === "web") {
    window.localStorage.removeItem(TOKEN_KEY);
  } else if (t) {
    if (!(await storage.secureSet(TOKEN_KEY, t))) throw new Error("Unable to securely save your session. Please try again.");
  }
  else if (!(await storage.secureRemove(TOKEN_KEY))) throw new Error("Unable to remove your saved session. Please retry logout.");
}

async function readToken(): Promise<string | null> {
  if (Platform.OS === "web") return null;
  return (await storage.secureGet(TOKEN_KEY, null)) as string | null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [signingIn, setSigningIn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nativeLoginPending = useRef(false);
  const sessions = useRef(new SessionWrites());

  const clear = useCallback(async () => {
    const version = sessions.current.next();
    setApiToken(null);
    if (Platform.OS === "web") setBrowserSession(null);
    setUser(null);
    await queryClient.cancelQueries();
    queryClient.clear();
    await sessions.current.save(version, () => saveToken(null));
  }, []);

  const acceptSession = useCallback(async (session: { session_token?: string; csrf_token?: string; user: User }) => {
    if (Platform.OS === "web" && !session.csrf_token) throw new Error("Browser cookie session was not established. Please sign in again.");
    if (Platform.OS !== "web" && !session.session_token) throw new Error("Native session was not established.");
    const version = sessions.current.next();
    setApiToken(null);
    setUser(null);
    await queryClient.cancelQueries();
    queryClient.clear();
    await sessions.current.save(version, () => saveToken(session.session_token || null));
    if (!sessions.current.current(version)) return;
    if (Platform.OS === "web") {
      setBrowserSession(session);
      window.localStorage.setItem("auth_changed", String(Date.now()));
    } else setApiToken(session.session_token!);
    setUser(session.user);
    setError(null);
  }, []);
  const refreshUser = useCallback(async () => {
    const version = sessions.current.version;
    const fresh = await api<User>("/auth/me");
    if (sessions.current.current(version)) setUser(fresh);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setError("Your session expired or was revoked. Please sign in again.");
      void clear().catch(() => setError("Signed out, but saved session removal failed. Please retry logout."));
    });
    (async () => {
      const version = sessions.current.version;
      try {
        if (Platform.OS === "web") {
          await saveToken(null);
          const initial = new URL(window.location.href);
          if (extractSessionId(initial.href)) {
            initial.searchParams.delete("session_id"); initial.hash = "";
            window.history.replaceState(window.history.state, "", initial.toString());
            setError("Managed web sign-in is unavailable. Use email or independent Google sign-in.");
          }
          const result = await bootstrapBrowser();
          if (sessions.current.current(version)) setUser(result.user);
          return;
        }
        const token = await readToken();
        if (!sessions.current.current(version)) return;
        if (token) {
          setApiToken(token);
          try {
            const fresh = await api<User>("/auth/me");
            if (sessions.current.current(version)) setUser(fresh);
          } catch (e: any) {
            // Only a real 401 signs the user out; offline/network errors keep the saved session.
            if (sessions.current.current(version)) {
              if (e?.status === 401) await clear();
              else setError("Unable to load your session. Check your connection and try signing in again.");
            }
          }
        }
      } catch (e: any) {
        setError(Platform.OS === "web" ? (e?.message || "Unable to initialize browser authentication") : "Unable to read your saved session. Please sign in again.");
      } finally {
        setLoading(false);
      }
    })();
    if (Platform.OS === "web") {
      const changed = (event: StorageEvent) => {
        if (event.key === "auth_changed") { void clear().then(() => window.location.reload()); }
      };
      window.addEventListener("storage", changed);
      return () => window.removeEventListener("storage", changed);
    }
  }, [clear]);

  const login = useCallback(async () => {
    if (nativeLoginPending.current) return;
    if (Platform.OS === "web") {
      setError("Use the Google button on this page; managed callback verification is unavailable.");
      return;
    }
    nativeLoginPending.current = true;
    setSigningIn(true);
    setError(null);
    const version = sessions.current.version;
    try {
      const idToken = await requestNativeGoogleToken();
      if (!idToken || !sessions.current.current(version)) return;
      const result = await api<{ session_token: string; user: User }>("/auth/google", {
        method: "POST", body: { id_token: idToken },
      });
      if (!sessions.current.current(version)) return;
      if (!result || typeof result.session_token !== "string" || !result.session_token || !result.user?.user_id) {
        throw new Error("invalid_session_response");
      }
      await acceptSession(result);
    } catch (e) {
      if (sessions.current.current(version)) setError(nativeGoogleError(e));
    } finally {
      nativeLoginPending.current = false;
      setSigningIn(false);
    }
  }, [acceptSession]);

  const logout = useCallback(async () => {
    const version = sessions.current.version;
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      if (Platform.OS === "web") {
        if (!sessions.current.current(version)) return;
        await clear();
        setError("Sign-out could not be confirmed by the server. Reconnect and retry sign-out before leaving this device.");
        return;
      }
    }
    if (sessions.current.current(version)) {
      try {
        await clear();
        if (Platform.OS === "web" && sessions.current.current(version + 1)) window.localStorage.setItem("auth_changed", String(Date.now()));
      }
      catch { setError("Signed out, but saved session removal failed. Please retry logout."); }
    }
  }, [clear]);

  return (
    <AuthContext.Provider value={{ user, loading, signingIn, error, login, logout, acceptSession, refreshUser }}>{children}</AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
