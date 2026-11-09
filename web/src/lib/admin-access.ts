import { parseStats, parseUser } from "./contracts.ts";

export type PrivateRead = (path: "/api/auth/me" | "/api/admin/stats") => Promise<{ status: number; data: unknown }>;
export async function checkAdmin(read: PrivateRead) {
  try {
    const response = await read("/api/auth/me");
    if (response.status === 401) return { kind: "signed-out" } as const;
    if (response.status !== 200) return { kind: "unavailable" } as const;
    const user = parseUser(response.data);
    if (user.role !== "admin") return { kind: "denied" } as const;
    return { kind: "allowed", user } as const;
  } catch { return { kind: "unavailable" } as const; }
}
export async function readAdminStats(read: PrivateRead) {
  // Never depend solely on a layout having checked the caller.
  const access = await checkAdmin(read);
  if (access.kind !== "allowed") return null;
  try {
    const response = await read("/api/admin/stats");
    return response.status === 200 ? parseStats(response.data) : null;
  } catch { return null; }
}
