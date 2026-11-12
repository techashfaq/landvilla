export type ProxyConfig = { backendOrigin: string; webOrigin: string; production: boolean };

export function readConfig(env: Record<string, string | undefined>): ProxyConfig {
  const production = env.NODE_ENV === "production";
  const transport = env.BACKEND_TRANSPORT || "https";
  if (!["https", "private-http"].includes(transport)) throw new Error("Invalid backend transport configuration.");
  if (transport === "private-http" && env.BACKEND_ORIGIN !== "http://api:8000") throw new Error("Private HTTP transport requires the fixed Docker API origin.");
  function origin(value: string | undefined, fallback: string, privateBackend = false) {
    if (production && !value) throw new Error("Production web origins are not configured.");
    const url = new URL(value || fallback);
    if (url.username || url.password || url.pathname !== "/" || url.search || url.hash || !["http:", "https:"].includes(url.protocol)) throw new Error("Invalid origin configuration.");
    if (url.protocol !== "https:" && !privateBackend && (production || !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname))) throw new Error("HTTPS is required outside local development.");
    return url.origin;
  }
  // The only production HTTP exception is this named service on our private
  // Docker network. No external hostname, IP range, URL alias or alternate port.
  const backendOrigin = origin(env.BACKEND_ORIGIN, "http://127.0.0.1:8000", transport === "private-http");
  const webOrigin = origin(env.WEB_ORIGIN, "http://localhost:19006");
  if (backendOrigin === webOrigin) throw new Error("Backend must not point back to this web server.");
  return { backendOrigin, webOrigin, production };
}
