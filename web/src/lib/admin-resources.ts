import { isRecord } from "./contracts.ts";
import { checkAdmin } from "./admin-access.ts";
import { adminPath, pagedEndpoints } from "./admin-routes.ts";
import { publicImage } from "./property-contracts.ts";

export const adminSections = {
  properties: { title: "Property management", endpoint: "listings", cap: 200, description: "Review submitted properties and record a moderation decision." },
  brokers: { title: "Broker applications", endpoint: "brokers", cap: 200, description: "Review broker applications and their private documents before deciding." },
  users: { title: "User management", endpoint: "users", cap: 100, description: "Search accounts and manage access with an audited reason." },
  enquiries: { title: "Enquiries and leads", endpoint: "enquiries", cap: 100, description: "Review enquiries and record status changes. Contact numbers and private conversations are not included in this list." },
  packages: { title: "Featured packages", endpoint: "featured-plans", cap: 50, description: "Configure package prices and durations. Existing payment records remain authoritative." },
  payments: { title: "Payment records", endpoint: "payments", cap: 200, description: "Existing order records only. These records do not replace settlement reconciliation or confirm receipt of funds." },
  locations: { title: "Locations", endpoint: "localities", cap: 1000, description: "Create, edit, verify and activate Ujjain localities. Zone and future-city configuration have separate views." },
  cms: { title: "Content management", endpoint: "cms", cap: 100, description: "Maintain homepage announcements, FAQs and support content. Publish only approved business text." },
  staff: { title: "Staff and permissions", endpoint: "staff", cap: 100, description: "Only a configured independent staff manager can grant or revoke access to existing accounts." },
  audit: { title: "Audit history", endpoint: "audit", cap: 100, description: "Search recorded actors, actions, targets and reasons." },
  cities: { title: "Cities", endpoint: "cities", cap: 100, description: "Prepare future markets as inactive. Ujjain remains the launch market." },
  zones: { title: "Zones", endpoint: "zones", cap: 100, description: "Manage Ujjain zone configuration." },
  reports: { title: "Abuse reports", endpoint: "reports", cap: 200, description: "Review reported content and resolve with an audited moderation reason." },
} as const;
export type AdminSection = keyof typeof adminSections;
export type AdminRecord = { id: string; title: string; status: string; ownerId: string; images: string[]; details: [string, string][]; documents: { id: string; name: string }[]; editable: Record<string, string | number | boolean> };
const text = (value: unknown) => typeof value === "string" ? value.slice(0, 4000) : typeof value === "number" && Number.isFinite(value) ? String(value) : typeof value === "boolean" ? (value ? "Yes" : "No") : "";

/** Project explicit fields. Never serialize arbitrary backend records or credentials. */
export function projectAdminRecord(section: AdminSection, value: unknown): AdminRecord {
  if (!isRecord(value)) throw new Error("Invalid record");
  const id = text(value.id || value.user_id);
  if (!/^[a-zA-Z0-9_-]{1,100}$/.test(id)) throw new Error("Invalid record identifier");
  const owner = isRecord(value.owner) ? value.owner : {};
  const locality = isRecord(value.locality) ? value.locality : {};
  const moderation = isRecord(value.moderation) ? value.moderation : {};
  const fields: Record<AdminSection, [string, unknown][]> = {
    properties: [["Purpose", value.purpose], ["Price (INR)", value.price], ["Type", value.type], ["BHK", value.bhk], ["Area (sq ft)", value.area_sqft], ["Locality", locality.name_en], ["Description", value.description_en], ["Owner", owner.name], ["Owner email", owner.email], ["Review note", moderation.note], ["Address", value.address], ["Lister role", value.posted_by_role], ["History", Array.isArray(value.moderation_history) ? value.moderation_history.map(h => isRecord(h) ? `${text(h.at)} · ${text(h.by)} · ${text(h.status)} · ${text(h.note)}` : "").join("\n") : ""], ["Updated", value.updated_at]],
    brokers: [["Phone", value.phone], ["Operating locality ID", value.locality_id], ["Firm", value.firm_name], ["Email", value.email], ["RERA number", value.rera_number], ["RERA status", value.rera_status], ["Review note", value.admin_note], ["Updated", value.updated_at]],
    packages: [["Price (INR)", value.price_inr], ["Duration (days)", value.duration_days], ["Active", value.is_active]],
    payments: [["Property", value.property_id], ["Plan", value.plan_slug], ["Amount (paise)", value.amount], ["Mode", value.mode], ["Refund status", value.refund_status], ["Created", value.created_at], ["Paid at", value.paid_at]],
    locations: [["Slug", value.slug], ["Zone", value.zone_id], ["Verification", value.verification_status], ["Active", value.is_active], ["Listings", value.listing_count]],
    audit: [["Actor", value.actor], ["Action", value.action], ["Target", value.target], ["Reason", value.note], ["Time", value.created_at]],
    reports: [["Target", value.target_label], ["Reason", value.reason], ["Note", value.note], ["Created", value.created_at]],
    users: [["Email", value.email], ["Role", value.role], ["Listings", value.listing_count], ["Enquiries", value.enquiry_count]],
    enquiries: [["Property", value.property_id], ["Lister", value.lister_user_id], ["Intent", value.intent], ["Message", value.message], ["Created", value.created_at]],
    cms: [["Kind", value.kind], ["Text", value.body], ["Link", value.link]],
    staff: [["Email", value.email], ["Permissions", Array.isArray(value.admin_permissions) ? value.admin_permissions.join(", ") : "Full administrator"]],
    cities: [["Slug", value.slug], ["Active", value.is_active]], zones: [["Slug", value.slug], ["City", value.city_id], ["Active", value.is_active]],
  };
  const docs = section === "brokers" && Array.isArray(value.documents) ? value.documents : [];
  const images = section === "properties" && Array.isArray(value.images) ? value.images.slice(0, 10).map(publicImage).filter((url): url is string => url !== null) : [];
  const editable: AdminRecord["editable"] = {};
  for (const key of ["name_en", "name_hi", "price_inr", "duration_days", "play_product_id", "benefits", "is_active", "zone_id", "title", "body", "kind", "link", "status", "slug"]) if (["string", "number", "boolean"].includes(typeof value[key])) editable[key] = value[key] as string | number | boolean;
  if (section === "staff") { editable.permissions = Array.isArray(value.admin_permissions) ? value.admin_permissions.join(", ") : ""; editable.enabled = true; }
  return { id, images, editable, title: text(value.title_en || value.title || value.full_name || value.name || value.name_en || value.target_label) || id, status: text(value.listing_status || value.status), ownerId: section === "brokers" ? id : text(owner.user_id), details: fields[section].map(([name, val]) => [name, text(val)] as [string, string]).filter(([, val]) => val !== ""), documents: docs.filter(doc => isRecord(doc) && typeof doc.id === "string" && /^[a-zA-Z0-9_-]{1,100}$/.test(doc.id)).map(doc => ({ id: String(doc.id), name: text(doc.name) || "Private verification document" })) };
}

export type AdminRead = (path: string) => Promise<{ status: number; data: unknown }>;
export async function readAdminRecords(read: AdminRead, section: AdminSection, status = "", q = "", page = 1) {
  const access = await checkAdmin(read);
  if (access.kind !== "allowed") return { kind: access.kind, items: [] } as const;
  const config = adminSections[section];
  if (!("endpoint" in config)) return { kind: "unsupported", items: [] } as const;
  try {
    const paged = pagedEndpoints.includes(config.endpoint);
    const query = new URLSearchParams({ ...(status ? { status } : {}), ...(paged ? { q, page: String(page), limit: "20" } : {}) });
    const path = adminPath("GET", "/api/admin/" + config.endpoint + (query.size ? "?" + query : ""));
    const response = await read(path);
    if (response.status === 401 || response.status === 403) return { kind: "denied", items: [] } as const;
    if (response.status !== 200 || !isRecord(response.data) || !Array.isArray(response.data.items) || response.data.items.length > config.cap) throw new Error("Unavailable");
    return { kind: "ready", items: response.data.items.map(item => projectAdminRecord(section, item)), viewerId: access.user.user_id, total: typeof response.data.total === "number" ? response.data.total : response.data.items.length, serverPaged: paged } as const;
  } catch { return { kind: "unavailable", items: [] } as const; }
}
