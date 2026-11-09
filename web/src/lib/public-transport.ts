import type { ProxyConfig } from "./config.ts";
import { parseMeta, parseProperty, parsePropertyPage } from "./property-contracts.ts";
import { propertyId, propertyQuery } from "./property-query.ts";

export class PublicApiError extends Error {
  readonly status: number;
  constructor(status: number) { super(status === 404 ? "This property or location is not available." : status === 400 || status === 422 ? "These filters could not be applied." : "Property information is temporarily unavailable. Please try again."); this.status = status; }
}
/** Server caller supplies validated fixed configuration, never a user-controlled URL. */
export function publicApi(config: ProxyConfig, transport: typeof fetch = fetch) {
  async function read<T>(path: string, parse: (value: unknown) => T): Promise<T> {
    try {
      const response = await transport(config.backendOrigin + path, { headers: { Accept: "application/json" }, credentials: "omit", cache: "no-store", redirect: "manual", signal: AbortSignal.timeout(12000) });
      if (!response.ok) throw new PublicApiError([400, 404, 422, 429].includes(response.status) ? response.status : 503);
      if (!response.headers.get("content-type")?.includes("application/json")) throw new PublicApiError(502);
      return parse(await response.json());
    } catch (error) { if (error instanceof PublicApiError) throw error; throw new PublicApiError(503); }
  }
  return {
    meta: () => read("/api/meta", parseMeta),
    properties: (input = new URLSearchParams()) => { const query = propertyQuery(input).toString(); return read("/api/properties" + (query ? "?" + query : ""), parsePropertyPage); },
    property: (id: string) => read("/api/properties/" + propertyId(id), parseProperty),
  };
}
