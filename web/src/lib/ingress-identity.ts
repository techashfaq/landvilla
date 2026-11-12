import { createHmac, timingSafeEqual } from "node:crypto";
import { isIP } from "node:net";

/** Dedicated hop credentials, never browser credentials or general application secrets. */
export function ingressSettings(env: Record<string, string | undefined>) {
  const token = env.LANDVILLA_INGRESS_TOKEN || "";
  const key = env.WEB_API_IP_KEY || "";
  if (env.CLIENT_IP_MODE !== "signed-v1" || !/^[a-f0-9]{64}$/.test(token) || !/^[a-f0-9]{64}$/.test(key) || token === key) {
    throw new Error("Ingress identity unavailable.");
  }
  return { token, key };
}
export function ingressIdentity(request: Request, env: Record<string, string | undefined>, now = Date.now()): Headers {
  const { token, key } = ingressSettings(env);
  const supplied = request.headers.get("x-lv-ingress-token") || "";
  const ip = request.headers.get("x-lv-client-ip") || "";
  if (!/^[a-f0-9]{64}$/.test(supplied) || !timingSafeEqual(Buffer.from(supplied), Buffer.from(token)) || !isIP(ip) || ip.includes("%")) {
    throw new Error("Ingress identity unavailable.");
  }
  const stamp = String(Math.floor(now / 1000));
  const path = new URL(request.url).pathname;
  const signature = createHmac("sha256", Buffer.from(key, "hex")).update(["v1", stamp, request.method, path, ip].join("\n")).digest("hex");
  return new Headers({ "X-LV-Client-IP": ip, "X-LV-IP-Time": stamp, "X-LV-IP-Signature": signature });
}
