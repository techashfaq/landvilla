/** Exact browser administration surface; authorization is independently enforced by FastAPI. */
export const listingStatuses = ["pending_review", "changes_requested", "active", "rejected", "inactive", "suspended", "expired", "sold_rented", "all"] as const;
export const brokerStatuses = ["pending", "approved", "rejected", "suspended", "all"] as const;
const reads = ["listings", "brokers", "users", "enquiries", "audit", "staff", "cms", "cities", "zones", "featured-plans", "payments", "localities", "reports", "contact-access-logs"];
export const pagedEndpoints = ["listings", "brokers", "users", "enquiries", "audit", "staff", "cms", "cities", "zones", "payments", "reports", "localities"];
const identifier = /^[a-zA-Z0-9_-]{1,100}$/;
export function resourceStatuses(resource: string): readonly string[] {
  return ({ listings: listingStatuses, properties: listingStatuses, brokers: brokerStatuses, reports: ["open", "resolved"], users: ["active", "suspended", "deleted"], enquiries: ["new", "contacted", "follow_up", "closed"], payments: ["created", "pending", "paid", "failed", "refunded", "creating", "creation_unknown", "verification_failed", "cancelled", "expired", "payment_review"] } as Record<string, readonly string[]>)[resource] ?? [];
}
export function adminPath(method: string, input: string): string {
  if (!input.startsWith("/api/admin/") || input.includes("#")) throw new Error("Invalid administrative path");
  const [path, query = ""] = input.split("?");
  if (!path || path.includes("%") || input.split("?").length > 2) throw new Error("Invalid administrative path");
  const parts = path.slice("/api/admin/".length).split("/");
  if (method === "GET" && parts.length === 1 && reads.includes(parts[0]!)) {
    const params = new URLSearchParams(query);
    const allowed = pagedEndpoints.includes(parts[0]!) ? ["status", "q", "page", "limit"] : ["status"];
    for (const key of params.keys()) if (!allowed.includes(key) || params.getAll(key).length !== 1) throw new Error("Invalid administrative query");
    if (params.has("status") && !resourceStatuses(parts[0]!).includes(params.get("status")!)) throw new Error("Invalid status");
    if ((params.get("q")?.length ?? 0) > 100 || (params.has("page") && !/^[1-9]\d{0,5}$/.test(params.get("page")!)) || (params.has("limit") && params.get("limit") !== "20")) throw new Error("Invalid pagination");
    return path + (params.size ? "?" + params.toString() : "");
  }
  if (method === "GET" && !query && parts.length === 2 && ["enquiries", "payments"].includes(parts[0]!) && identifier.test(parts[1]!)) return path;
  if (!query && method === "POST" && parts.length === 1 && ["featured-plans", "localities", "cms", "zones", "cities"].includes(parts[0]!)) return path;
  if (!query && parts.length === 2 && identifier.test(parts[1]!) && ((method === "PUT" && ["featured-plans", "cms", "zones"].includes(parts[0]!)) || (method === "PATCH" && parts[0] === "localities"))) return path;
  if (method === "POST" && !query && parts.length === 3 && identifier.test(parts[1] || "")) {
    const actions = ({ listings: ["approve", "reject", "request-changes", "suspend", "deactivate", "reactivate"], brokers: ["approve", "reject", "suspend"], users: ["suspend", "reactivate"], enquiries: ["status"], reports: ["resolve"], staff: ["permissions"], payments: [], localities: ["activate", "deactivate", "verify"] } as Record<string, string[]>)[parts[0]!] ?? [];
    if (actions.includes(parts[2]!)) return path;
  }
  throw new Error("Unsupported administrative operation");
}
export function adminRoute(method: string, path: string): boolean { try { adminPath(method, path); return true; } catch { return false; } }
export function moderationBody(action: string, note: string) {
  const clean = note.trim();
  if (!["approve", "reject", "request-changes", "suspend", "deactivate", "reactivate"].includes(action) || clean.length > 1000 || (action !== "approve" && clean.length < 5)) throw new Error("Enter a reason of 5 to 1,000 characters for this decision.");
  return { note: clean };
}
export function moderationActions(kind: "listings" | "brokers", status: string, self: boolean): string[] {
  if (self) return [];
  if (kind === "brokers") return status === "pending" ? ["approve", "reject"] : status === "approved" ? ["suspend"] : status === "suspended" ? ["approve"] : [];
  if (["inactive", "suspended"].includes(status)) return ["reactivate"];
  return ["pending_review", "changes_requested", "active"].includes(status) ? (status === "active" ? ["request-changes", "reject", "deactivate", "suspend"] : ["approve", "request-changes", "reject", "deactivate", "suspend"]) : [];
}
