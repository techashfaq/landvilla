/** Exact reviewed customer routes only. No administrative or payment mutations. */
export function accountRoute(method: string, path: string) {
  const id = "[a-zA-Z0-9_-]{1,100}";
  const matches = (pattern: string) => new RegExp(`^/api/${pattern}$`).test(path);
  if (method === "GET") return ["/api/me/profile", "/api/saved", "/api/enquiries/me", "/api/listings/mine", "/api/me/lister", "/api/leads"].includes(path) || matches(`enquiries/${id}`) || matches(`leads/${id}`) || matches(`listings/${id}/edit`);
  if (method === "POST") return ["/api/enquiries", "/api/listings", "/api/broker/apply"].includes(path) || matches(`saved/${id}`) || matches(`enquiries/${id}/messages`);
  if (method === "PATCH") return path === "/api/me/profile" || matches(`leads/${id}`);
  if (method === "PUT") return matches(`listings/${id}`);
  return method === "DELETE" && matches(`saved/${id}`);
}
export function accountPath(method: string, input: string): string {
  const url = new URL(input, "http://web.invalid");
  if (!input.startsWith("/api/") || url.origin !== "http://web.invalid" || url.hash || !accountRoute(method, url.pathname)) throw new Error("Unsupported account route.");
  if (url.search && (method !== "GET" || url.pathname !== "/api/listings/mine")) throw new Error("Unsupported account query.");
  for (const [key, value] of url.searchParams) {
    const n = Number(value);
    if (!["page", "limit"].includes(key) || url.searchParams.getAll(key).length !== 1 || !/^\d+$/.test(value) || !Number.isSafeInteger(n) || n < 1 || (key === "limit" && n > 100)) throw new Error("Invalid listing pagination.");
  }
  url.searchParams.sort(); return url.pathname + url.search;
}
