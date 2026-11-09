import { Platform } from "react-native";


const configuredBase = (process.env.EXPO_PUBLIC_BACKEND_URL || "").trim().replace(/\/+$/, "");
const BASE = `${configuredBase}/api`;

let authToken: string | null = null;
let onUnauthorized: (() => void) | null = null;
let csrfToken: string | null = null;
let sessionVersion = 0;
let bootstrapPending: Promise<any> | null = null;

export function setApiToken(t: string | null) {
  authToken = Platform.OS === "web" ? null : t;
  sessionVersion++;
}
export function setBrowserSession(session: { csrf_token?: string } | null) {
  csrfToken = session?.csrf_token || null;
  sessionVersion++;
}
export async function bootstrapBrowser() {
  if (!bootstrapPending) {
    const version = sessionVersion;
    bootstrapPending = api("/auth/browser/bootstrap").then(result => {
      if (version !== sessionVersion) throw new ApiError(409, "Browser session changed. Please retry.");
      setBrowserSession(result); return result;
    }).finally(() => { bootstrapPending = null; });
  }
  return bootstrapPending;
}
export async function authHeaders(): Promise<Record<string, string>> {
  if (Platform.OS === "web") {
    if (!csrfToken) await bootstrapBrowser();
    return { "X-LV-Client": "web", "X-CSRF-Token": csrfToken! };
  }
  return authToken ? { Authorization: `Bearer ${authToken}`, "X-LV-Client": Platform.OS } : { "X-LV-Client": Platform.OS };
}
export function getApiToken() {
  return authToken;
}
export const API_BASE = BASE;
export const BACKEND = configuredBase;

/** Absolute URL for an image/file. Uploaded files are served by our backend under /api/files. */
export function fileUrl(u: string, withToken = false) {
  if (!u) return u;
  const abs = /^https?:\/\//i.test(u) ? u : u.startsWith("/") && !u.startsWith("//") ? `${BACKEND}${u}` : "";
  return Platform.OS !== "web" && withToken && authToken && !u.startsWith("http") ? `${abs}?token=${encodeURIComponent(authToken)}` : abs;
}

export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: any } = {}): Promise<T> {
  if (!/^https?:\/\//i.test(BACKEND)) throw new ApiError(0, "Backend URL is not configured");
  const requestToken = authToken;
  const unsafe = !["GET", "HEAD", "OPTIONS"].includes((opts.method || "GET").toUpperCase());
  if (Platform.OS === "web" && unsafe && !csrfToken) await bootstrapBrowser();
  const requestVersion = sessionVersion;
  const headers: Record<string, string> = { "Content-Type": "application/json", "X-LV-Client": Platform.OS };
  if (Platform.OS === "web") { if (csrfToken) headers["X-CSRF-Token"] = csrfToken; }
  else if (requestToken) headers.Authorization = `Bearer ${requestToken}`;
  const res = await fetch(`${BASE}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    credentials: Platform.OS === "web" ? "include" : "omit",
  });
  const text = await res.text();
  let data: any = null;
  try { data = text ? JSON.parse(text) : null; } catch {
    if (res.status === 401 && requestVersion === sessionVersion && onUnauthorized) onUnauthorized();
    throw new ApiError(res.status, "The server returned an invalid response. Please try again.");
  }
  if (!res.ok) {
    if (res.status === 401 && requestVersion === sessionVersion && onUnauthorized) onUnauthorized();
    let msg = "Something went wrong";
    if (typeof data?.detail === "string") msg = data.detail;
    else if (Array.isArray(data?.detail))
      msg = data.detail
        .map((d: any) => {
          const field = Array.isArray(d.loc) ? String(d.loc[d.loc.length - 1]).replace(/_/g, " ") : "";
          return `${field ? field[0].toUpperCase() + field.slice(1) + ": " : ""}${String(d.msg).replace("Value error, ", "")}`;
        })
        .join(", ");
    throw new ApiError(res.status, msg);
  }
  return data as T;
}

export function qs(params: Record<string, any>) {
  const p = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "" && !(Array.isArray(v) && v.length === 0))
    .map(([k, v]) => `${k}=${encodeURIComponent(Array.isArray(v) ? v.join(",") : String(v))}`);
  return p.length ? `?${p.join("&")}` : "";
}
