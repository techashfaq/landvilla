"use client";
import { useEffect } from "react";
import Link from "next/link";
import { useSession } from "@/components/session-provider";
export function AccountGate({ children }: { children: React.ReactNode }) {
  const { client, session, loading, error } = useSession();
  useEffect(() => { void client.bootstrap().catch(() => {}); }, [client]);
  if (loading) return <p role="status">Checking your session…</p>;
  if (!session?.user) return <div className="panel stack"><h1>Sign in to continue.</h1><p>{error || "Your account information is available after sign-in."}</p><Link className="button" href="/login">Open account access</Link></div>;
  // Remount all private component state on a session/account change. Backend authorizes every request.
  return <div key={session.user.user_id + session.csrf_token}>{children}</div>;
}
