import type { ProxyConfig } from "./config.ts";

/** No caller headers are accepted here. Uvicorn trusts only the web service IP. */
export function backendHeaders(config: ProxyConfig): Headers {
  return new Headers({
    Accept: "application/json",
    "X-Forwarded-Proto": new URL(config.webOrigin).protocol.slice(0, -1),
  });
}
