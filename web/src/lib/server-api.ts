import "server-only";
import { cookies } from "next/headers";
import { readConfig } from "./config";
import { backendHeaders } from "./backend-headers";
import { checkAdmin, readAdminStats } from "./admin-access";
import { sessionCookie } from "./session-cookie";

async function privateRead(path: "/api/auth/me" | "/api/admin/stats") {
  const config = readConfig(process.env);
  const jar = await cookies();
  const name = config.production || config.webOrigin.startsWith("https:") ? "__Host-lv_session" : "lv_dev_session";
  const cookie = sessionCookie(jar.getAll(name).map(item => `${name}=${item.value}`).join("; "), name.startsWith("__Host-"));
  if (!cookie) return { status: 401, data: null };
  const headers = backendHeaders(config);
  headers.set("Cookie", cookie);
  headers.set("X-LV-Client", "web");
  const response = await fetch(config.backendOrigin + path, {
    headers,
    cache: "no-store", redirect: "error", signal: AbortSignal.timeout(10000),
  });
  return { status: response.status, data: response.ok ? await response.json() as unknown : null };
}
export async function adminAccess() {
  return checkAdmin(privateRead);
}
export async function dashboardStats() {
  return readAdminStats(privateRead);
}
