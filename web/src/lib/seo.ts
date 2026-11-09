/** Canonicals use an explicitly configured origin; prelaunch remains noindex. */
export function canonicalOrigin(env: Record<string, string | undefined>): string | null {
  try {
    if (!env.WEB_ORIGIN) return null;
    const url = new URL(env.WEB_ORIGIN);
    if (url.username || url.password || url.pathname !== "/" || url.search || url.hash) return null;
    if (url.protocol !== "https:" && !(env.NODE_ENV !== "production" && url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname))) return null;
    return url.origin;
  } catch { return null; }
}
