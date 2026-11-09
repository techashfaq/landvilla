import "server-only";
import { cookies } from "next/headers";
import { readConfig } from "./config";
import { checkAdmin, readAdminStats } from "./admin-access";

async function privateRead(path: "/api/auth/me" | "/api/admin/stats") {
  const config = readConfig(process.env);
  const jar = await cookies();
  const name = config.production || config.webOrigin.startsWith("https:") ? "__Host-lv_session" : "lv_dev_session";
  const cookie = jar.get(name);
  if (!cookie) return { status: 401, data: null };
  const response = await fetch(config.backendOrigin + path, {
    headers: { Cookie: `${name}=${cookie.value}`, "X-LV-Client": "web", Accept: "application/json" },
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
