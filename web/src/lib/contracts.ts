export type User = { user_id: string; name: string | null; email: string; picture?: string | null; role: string };
export type Session = { user: User | null; csrf_token: string; expires_in: number };
export type OtpChallenge = { challenge_id: string; expires_in: number; resend_after: number; message: string };
export type Registration = { first_name: string; last_name: string; email: string; mobile: string; account_role: "buyer" | "owner" | "broker" | "builder"; accept_terms: true; accept_privacy: true };
export type OtpRequest = { identifier: string; purpose: "login" | "register"; registration?: Registration };
export type AdminStats = { pending_listings: number; pending_brokers: number; open_reports: number; paid_orders: number };

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
export function parseUser(value: unknown): User {
  if (!isRecord(value) || typeof value.user_id !== "string" || typeof value.email !== "string" || typeof value.role !== "string" || !(value.name === null || typeof value.name === "string")) throw new Error("Invalid account response. Please try again.");
  // Allowlist; never pass through backend security metadata.
  return { user_id: value.user_id, name: value.name, email: value.email, role: value.role };
}
export function parseSession(value: unknown): Session {
  if (!isRecord(value) || "session_token" in value || typeof value.csrf_token !== "string" || !value.csrf_token || typeof value.expires_in !== "number" || value.expires_in <= 0) throw new Error("Browser session could not be established. Reload and try again.");
  return { user: value.user === null ? null : parseUser(value.user), csrf_token: value.csrf_token, expires_in: value.expires_in };
}
export function parseChallenge(value: unknown): OtpChallenge {
  if (!isRecord(value) || typeof value.challenge_id !== "string" || value.challenge_id.length < 20 || typeof value.resend_after !== "number" || value.resend_after < 0 || typeof value.expires_in !== "number" || value.expires_in <= 0) throw new Error("Could not start verification. Please retry.");
  return { challenge_id: value.challenge_id, expires_in: value.expires_in, resend_after: value.resend_after, message: "If eligible, a verification code has been sent." };
}
export function parseStats(value: unknown): AdminStats {
  if (!isRecord(value)) throw new Error("Dashboard response is unavailable.");
  const keys = ["pending_listings", "pending_brokers", "open_reports", "paid_orders"] as const;
  const result = {} as AdminStats;
  for (const key of keys) {
    const count = value[key];
    if (typeof count !== "number" || !Number.isSafeInteger(count) || count < 0) throw new Error("Dashboard response is unavailable.");
    result[key] = count;
  }
  return result;
}
