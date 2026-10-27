import { Platform } from "react-native";


const BASE = `${process.env.EXPO_PUBLIC_BACKEND_URL}/api`;

let authToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setApiToken(t: string | null) {
  authToken = t;
}
export function getApiToken() {
  return authToken;
}
export const API_BASE = BASE;
export const BACKEND = process.env.EXPO_PUBLIC_BACKEND_URL as string;

/** Absolute URL for an image/file. Uploaded files are served by our backend under /api/files. */
export function fileUrl(u: string, withToken = false) {
  if (!u) return u;
  const abs = u.startsWith("http") ? u : `${BACKEND}${u}`;
  return withToken && authToken && !u.startsWith("http") ? `${abs}?token=${encodeURIComponent(authToken)}` : abs;
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
  const headers: Record<string, string> = { "Content-Type": "application/json", "X-LV-Client": Platform.OS };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  const res = await fetch(`${BASE}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    if (res.status === 401 && authToken && onUnauthorized) onUnauthorized();
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
