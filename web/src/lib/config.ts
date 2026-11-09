export type ProxyConfig = { backendOrigin: string; webOrigin: string; production: boolean };

export function readConfig(env: Record<string, string | undefined>): ProxyConfig {
  const production = env.NODE_ENV === "production";
  function origin(value: string | undefined, fallback: string) {
    if (production && !value) throw new Error("Production web origins are not configured.");
    const url = new URL(value || fallback);
    if (url.username || url.password || url.pathname !== "/" || url.search || url.hash || !["http:", "https:"].includes(url.protocol)) throw new Error("Invalid origin configuration.");
    if (url.protocol !== "https:" && (production || !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname))) throw new Error("HTTPS is required outside local development.");
    return url.origin;
  }
  const backendOrigin = origin(env.BACKEND_ORIGIN, "http://127.0.0.1:8000");
  const webOrigin = origin(env.WEB_ORIGIN, "http://localhost:19006");
  if (backendOrigin === webOrigin) throw new Error("Backend must not point back to this web server.");
  return { backendOrigin, webOrigin, production };
}
