import "server-only";
import { cookies } from "next/headers";
import { readConfig } from "./config";
import { backendHeaders } from "./backend-headers";
import { readAdminRecords, type AdminSection } from "./admin-resources";
import { sessionCookie } from "./session-cookie";

export async function adminRecords(section: AdminSection, status: string, q = "", page = 1) {
  return readAdminRecords(async path => {
    const config = readConfig(process.env);
    const name = config.production || config.webOrigin.startsWith("https:") ? "__Host-lv_session" : "lv_dev_session";
    const cookie = sessionCookie((await cookies()).getAll(name).map(item => `${name}=${item.value}`).join("; "), name.startsWith("__Host-"));
    if (!cookie) return { status: 401, data: null };
    const headers = backendHeaders(config);
    headers.set("Cookie", cookie);
    headers.set("X-LV-Client", "web");
    const response = await fetch(config.backendOrigin + path, { headers, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(10000) });
    return { status: response.status, data: response.ok ? await response.json() as unknown : null };
  }, section, status, q, page);
}
