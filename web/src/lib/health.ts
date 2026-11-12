import { readConfig } from "./config.ts";
import { backendHeaders } from "./backend-headers.ts";
import { ingressSettings } from "./ingress-identity.ts";

function result(ready: boolean) {
  return Response.json({ status: ready ? "ok" : "unavailable" }, {
    status: ready ? 200 : 503,
    headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" },
  });
}

export async function health(env: Record<string, string | undefined>, checkDependencies = false, transport: typeof fetch = fetch): Promise<Response> {
  try {
    const config = readConfig(env);
    if (config.production) ingressSettings(env);
    if (checkDependencies) {
      const response = await transport(config.backendOrigin + "/ready", {
        headers: backendHeaders(config), credentials: "omit", cache: "no-store",
        // API has a five-second dependency budget; allow transport headroom.
        redirect: "error", signal: AbortSignal.timeout(7000),
      });
      // Never return upstream diagnostics, cookies or dependency details.
      const ready = response.status === 200;
      await response.body?.cancel();
      return result(ready);
    }
    return result(true);
  } catch { return result(false); }
}
