import "server-only";
import { cookies } from "next/headers";
import { readConfig } from "./config";
import { readAdminRecords, type AdminSection } from "./admin-resources";

export async function adminRecords(section: AdminSection, status: string, q = "", page = 1) {
  return readAdminRecords(async path => {
    const config = readConfig(process.env);
    const name = config.production || config.webOrigin.startsWith("https:") ? "__Host-lv_session" : "lv_dev_session";
    const cookie = (await cookies()).get(name);
    if (!cookie) return { status: 401, data: null };
    const response = await fetch(config.backendOrigin + path, { headers: { Cookie: `${name}=${cookie.value}`, "X-LV-Client": "web", Accept: "application/json" }, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(10000) });
    return { status: response.status, data: response.ok ? await response.json() as unknown : null };
  }, section, status, q, page);
}
