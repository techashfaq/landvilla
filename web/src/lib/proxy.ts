import type { ProxyConfig } from "./config.ts";
import { accountPath, accountRoute } from "./account-routes.ts";
import { limitedBody, mediaRoute, mediaTypes, validateUpload } from "./media.ts";
import { propertyQuery } from "./property-query.ts";
import { adminPath, adminRoute } from "./admin-routes.ts";
import { publicPropertiesResponse, publicPropertyResponse } from "./public-response.ts";

// Explicit route policies; backend authorizes every protected read and mutation.
export function allowedRoute(method: string, path: string): boolean {
  const reads = ["/api/meta", "/api/auth/me", "/api/auth/browser/bootstrap", "/api/me/profile", "/api/admin/stats"];
  const writes = ["/api/auth/otp/request", "/api/auth/otp/verify", "/api/auth/google", "/api/auth/browser/google-nonce", "/api/auth/logout"];
  const publicPropertyRead = method === "GET" && (path === "/api/properties" || /^\/api\/properties\/[a-zA-Z0-9_-]{1,100}$/.test(path));
  return mediaRoute(method, path) || accountRoute(method, path) || adminRoute(method, path) || publicPropertyRead || (method === "GET" && (reads.includes(path) || /^\/api\/legal\/(privacy|terms)\.json$/.test(path))) || (method === "POST" && writes.includes(path));
}
export function sessionCookie(raw: string | null, production: boolean): string | null {
  const name = production ? "__Host-lv_session" : "lv_dev_session";
  const matches = (raw || "").split(";").map(x => x.trim()).filter(x => x.startsWith(name + "="));
  return matches.length === 1 ? matches[0]! : null;
}
function fail(status: number, detail: string) {
  return Response.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}
function validCookie(header: string, secure: boolean): boolean {
  const parts = header.split(";").map(part => part.trim().toLowerCase());
  const expected = secure ? "__host-lv_session=" : "lv_dev_session=";
  return !!parts[0]?.startsWith(expected) && parts.includes("httponly") && parts.includes("path=/") && parts.includes("samesite=lax") &&
    !parts.some(part => part.startsWith("domain=")) && (!secure || parts.includes("secure"));
}
export async function forward(request: Request, config: ProxyConfig, transport: typeof fetch = fetch): Promise<Response> {
  const url = new URL(request.url);
  const publicRead = request.method === "GET" && (url.pathname === "/api/properties" || url.pathname.startsWith("/api/properties/"));
  if (!allowedRoute(request.method, url.pathname)) return fail(404, "This API route is not available in the web foundation.");
  if (request.headers.has("authorization")) return fail(400, "Unsupported request credentials or query parameters.");
  let upstreamPath = url.pathname;
  if (url.search) {
    if (request.method === "GET" && url.pathname === "/api/properties") {
      try {
        const query = propertyQuery(url.searchParams);
        upstreamPath = url.pathname + (query.size ? "?" + query.toString() : "");
      } catch { return fail(400, "Unsupported query parameters."); }
    } else if (url.pathname.startsWith("/api/admin/")) {
      try { upstreamPath = adminPath(request.method, url.pathname + url.search); }
      catch { return fail(400, "Unsupported query parameters."); }
    } else {
      try { upstreamPath = accountPath(request.method, url.pathname + url.search); }
      catch { return fail(400, "Unsupported query parameters."); }
    }
  }
  const suppliedOrigin = request.headers.get("origin");
  if (suppliedOrigin && suppliedOrigin !== config.webOrigin) return fail(403, "Untrusted request origin.");
  if (request.headers.get("sec-fetch-site") === "cross-site") return fail(403, "Cross-site requests are not allowed.");
  const unsafe = !["GET", "HEAD", "OPTIONS"].includes(request.method);
  if (unsafe && suppliedOrigin !== config.webOrigin) return fail(403, "A same-origin request is required.");
  if (unsafe && !request.headers.get("x-csrf-token")) return fail(403, "Initialize your browser session before continuing.");
  const headers = new Headers({ "X-LV-Client": "web", Accept: "application/json" });
  const cookie = sessionCookie(request.headers.get("cookie"), config.production || new URL(config.webOrigin).protocol === "https:");
  if (cookie && !publicRead) headers.set("Cookie", cookie);
  for (const name of ["origin", "referer", "sec-fetch-site", "sec-fetch-mode", "x-csrf-token"]) {
    const value = request.headers.get(name);
    if (value && !(publicRead && name === "x-csrf-token")) headers.set(name, value);
  }
  // No forwarded IP/host/scheme supplied by the caller is trusted or relayed.
  let body: string | FormData | undefined;
  if (url.pathname === "/api/uploads") {
    if (!request.headers.get("content-type")?.startsWith("multipart/form-data;")) return fail(415, "Multipart upload required.");
    try {
      const bytes = await limitedBody(request, 11 * 1024 * 1024);
      const parsed = await new Response(bytes, { headers: { "Content-Type": request.headers.get("content-type")! } }).formData();
      body = await validateUpload(parsed);
    } catch { return fail(400, "Invalid upload. Check file type, size and contents."); }
  } else if (unsafe) {
    if (request.headers.get("content-type")?.split(";")[0] !== "application/json") return fail(415, "JSON request required.");
    if (Number(request.headers.get("content-length") || 0) > 32768) return fail(413, "Request too large.");
    const reader = request.body?.getReader();
    const chunks: Uint8Array[] = []; let bytes = 0;
    if (reader) {
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        bytes += chunk.value.byteLength;
        if (bytes > 32768) { await reader.cancel(); return fail(413, "Request too large."); }
        chunks.push(chunk.value);
      }
    }
    const joined = new Uint8Array(bytes); let offset = 0;
    for (const chunk of chunks) { joined.set(chunk, offset); offset += chunk.byteLength; }
    body = new TextDecoder().decode(joined);
    try { JSON.parse(body); } catch { return fail(400, "Invalid JSON request."); }
    headers.set("Content-Type", "application/json");
  }
  try {
    const upstream = await transport(config.backendOrigin + upstreamPath, { method: request.method, headers, body, cache: "no-store", redirect: "manual", signal: AbortSignal.timeout(body instanceof FormData ? 60000 : 15000) });
    if (upstream.status >= 300 && upstream.status < 400) return fail(502, "Unexpected API redirect.");
    if (url.pathname.startsWith("/api/files/") && upstream.ok) {
      const type = upstream.headers.get("content-type")?.split(";")[0] || "";
      if (!mediaTypes.includes(type)) return fail(502, "Unsupported file response.");
      return new Response(upstream.body, { status: 200, headers: { "Content-Type": type, "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox; default-src 'none'", ...(type === "application/pdf" ? { "Content-Disposition": 'attachment; filename="landvilla-document.pdf"' } : {}) } });
    }
    if (!upstream.headers.get("content-type")?.includes("application/json")) return fail(502, "The API returned an unexpected response.");
    const responseHeaders = new Headers({ "Content-Type": "application/json", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" });
    if (publicRead) {
      if (!upstream.ok) return fail(upstream.status >= 500 ? 503 : upstream.status, upstream.status === 404 ? "This property is not available." : "Property information could not be loaded.");
      try {
        const data: unknown = await upstream.json();
        return Response.json(url.pathname === "/api/properties" ? publicPropertiesResponse(data) : publicPropertyResponse(data), { headers: responseHeaders });
      } catch { return fail(502, "The API returned invalid property information."); }
    }
    // Preserve separate cookie headers, including cookie deletion attributes.
    for (const cookieHeader of upstream.headers.getSetCookie()) {
      if (!validCookie(cookieHeader, config.production || config.webOrigin.startsWith("https:"))) return fail(502, "Backend cookie configuration does not match this website.");
      responseHeaders.append("Set-Cookie", cookieHeader);
    }
    const retryAfter = upstream.headers.get("retry-after");
    if (retryAfter && /^\d{1,6}$/.test(retryAfter)) responseHeaders.set("Retry-After", retryAfter);
    if (upstream.status >= 500) return fail(503, "The service is temporarily unavailable. Check backend connectivity and configuration.");
    return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch {
    return fail(503, "The backend is unavailable. Please try again later.");
  }
}
