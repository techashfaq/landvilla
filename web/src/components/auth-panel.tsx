"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ApiError } from "@/lib/browser-client";
import type { OtpChallenge, OtpRequest } from "@/lib/contracts";
import { loginRequest, registrationRequest } from "@/lib/otp";
import { useSession } from "./session-provider";
import { GoogleButton } from "./google-button";

export function AuthPanel() {
  const { client, session, loading, error: sessionError } = useSession();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [challenge, setChallenge] = useState<OtpChallenge | null>(null);
  const [request, setRequest] = useState<OtpRequest | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [error, setError] = useState("");
  const [resendAt, setResendAt] = useState(0);
  const [seconds, setSeconds] = useState(0);
  useEffect(() => { void client.bootstrap().catch(() => {}); }, [client]);
  useEffect(() => {
    const timer = setInterval(() => setSeconds(Math.max(0, Math.ceil((resendAt - Date.now()) / 1000))), 500);
    return () => clearInterval(timer);
  }, [resendAt]);
  async function run(action: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError("");
    try { await action(); }
    catch (e) {
      setError(e instanceof Error ? e.message : "The request could not be completed.");
      if (e instanceof ApiError && e.retryAfter) { setResendAt(Date.now() + e.retryAfter * 1000); setSeconds(e.retryAfter); }
    } finally { lock.current = false; setBusy(false); }
  }
  async function send(input: OtpRequest) {
    const result = await client.requestOtp(input);
    setRequest(input); setChallenge(result); setCode("");
    setResendAt(Date.now() + result.resend_after * 1000); setSeconds(result.resend_after);
  }
  if (loading) return <div className="panel" role="status">Connecting to your secure browser session…</div>;
  if (session?.user) return <div className="panel stack">
    <span className="eyebrow">You’re signed in</span><h2>Welcome, {session.user.name || "there"}.</h2>
    <p>Your LANDVILLA account is connected.</p><Link className="button" href="/account">Open your account</Link>
    {session.user.role === "admin" && <Link className="button" href="/admin">Open admin dashboard</Link>}
    <button className="button secondary" disabled={busy} onClick={() => void run(async () => { await client.logout(); setChallenge(null); setRequest(null); })}>Sign out</button>
    {error && <p role="alert" className="notice error">{error}</p>}
  </div>;
  if (!session) return <div className="panel stack"><h2>Unable to initialize sign-in</h2><p role="alert" className="notice error">{sessionError || error || "The backend is not available."}</p><p>Confirm that the API is running and allows this website’s origin. No account has been created by this page.</p><button className="button" disabled={busy} onClick={() => void run(async () => { await client.bootstrap(); })}>Retry connection</button></div>;
  return <div className="panel stack">
    <div className="segmented" aria-label="Account access">
      <button aria-pressed={mode === "login"} disabled={busy || !!challenge} onClick={() => { setMode("login"); setError(""); }}>Sign in</button>
      <button aria-pressed={mode === "register"} disabled={busy || !!challenge} onClick={() => { setMode("register"); setError(""); }}>Create account</button>
    </div>
    {challenge ? <form className="stack" onSubmit={event => { event.preventDefault(); void run(async () => { await client.verifyOtp(challenge.challenge_id, code); setCode(""); setRequest(null); setChallenge(null); }); }}>
      <h2>Check your inbox or messages</h2><p>{challenge.message} Codes expire after five minutes. An account must be eligible to receive a code.</p>
      <label>Six-digit code<input name="code" value={code} onChange={e => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required /></label>
      <button className="button" disabled={busy || code.length !== 6}>{busy ? "Verifying…" : "Verify and sign in"}</button>
      <button className="button secondary" type="button" disabled={busy || seconds > 0 || !request} onClick={() => { if (request) void run(() => send(request)); }}>{seconds ? `Resend in ${seconds}s` : "Resend code"}</button>
      <button className="text-button" type="button" disabled={busy} onClick={() => { setChallenge(null); setRequest(null); setCode(""); setError(""); }}>Change details</button>
    </form> : <>
      <form className="stack" onSubmit={event => {
        event.preventDefault(); const form = new FormData(event.currentTarget);
        void run(() => send(mode === "register" ? registrationRequest(form) : loginRequest(String(form.get("identifier") || ""))));
      }}>
        <h2>{mode === "register" ? "Make yourself at home." : "Welcome back."}</h2>
        <p>{mode === "register" ? "Verify your email to create an account. Broker approval is a separate process." : "Use an email or mobile number already verified on your account."}</p>
        {mode === "register" ? <>
          <div className="form-row"><label>First name<input name="first_name" autoComplete="given-name" maxLength={60} required /></label><label>Last name<input name="last_name" autoComplete="family-name" maxLength={60} required /></label></div>
          <label>Email<input type="email" name="email" autoComplete="email" maxLength={254} required /></label>
          <label>Mobile with country code<input type="tel" name="mobile" placeholder="+91" autoComplete="tel" maxLength={20} required /></label>
          <label>I’m here as<select name="account_role" defaultValue="buyer"><option value="buyer">Buyer / property seeker</option><option value="owner">Property owner</option><option value="broker">Broker / agent</option><option value="builder">Builder / developer</option></select></label>
          <label className="check"><input name="accept_terms" type="checkbox" required /><span>I accept the <Link href="/legal/terms" target="_blank" rel="noopener">terms</Link>.</span></label>
          <label className="check"><input name="accept_privacy" type="checkbox" required /><span>I accept the <Link href="/legal/privacy" target="_blank" rel="noopener">privacy policy</Link>.</span></label>
        </> : <label>Email or mobile<input name="identifier" type="text" autoComplete="username" maxLength={254} placeholder="Email or +91 mobile number" required /></label>}
        <button className="button" disabled={busy || seconds > 0}>{busy ? "Requesting code…" : seconds ? `Try again in ${seconds}s` : "Send verification code"}</button>
      </form>
      <div className="divider"><span>or</span></div><GoogleButton />
      <p className="small muted">By continuing with Google, you agree to the <Link href="/legal/terms">terms</Link> and <Link href="/legal/privacy">privacy policy</Link>.</p>
    </>}
    {error && <p role="alert" className="notice error">{error}</p>}
    {sessionError && <p role="alert" className="notice error">{sessionError}</p>}
  </div>;
}
