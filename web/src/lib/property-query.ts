/** Only filters implemented by the current Ujjain property endpoint. */
export const propertyQueryKeys = ["purpose", "segment", "type", "locality", "zone", "min_price", "max_price", "bhk", "q", "sort", "page", "limit"] as const;
export class InvalidPropertyQuery extends Error {
  constructor() { super("Check the property filters. One or more values are unsupported or invalid."); }
}
export function propertyQuery(input: URLSearchParams): URLSearchParams {
  const output = new URLSearchParams();
  for (const [key, raw] of input) {
    if (!(propertyQueryKeys as readonly string[]).includes(key) || input.getAll(key).length !== 1) throw new InvalidPropertyQuery();
    const value = raw.trim();
    if (!value) continue;
    if (value.length > 300 || /[\u0000-\u001f\u007f]/.test(value)) throw new InvalidPropertyQuery();
    if (key === "purpose" && !["buy", "rent"].includes(value)) throw new InvalidPropertyQuery();
    if (key === "sort" && !["newest", "price_asc", "price_desc"].includes(value)) throw new InvalidPropertyQuery();
    if (["segment", "type", "zone"].includes(key) && !/^[a-zA-Z0-9_-]{1,100}$/.test(value)) throw new InvalidPropertyQuery();
    if (key === "locality" && !/^[a-zA-Z0-9_-]{1,100}(,[a-zA-Z0-9_-]{1,100}){0,9}$/.test(value)) throw new InvalidPropertyQuery();
    if (key === "bhk" && !/^(?:[1-9]|1[0-9]|20|4\+)(?:,(?:[1-9]|1[0-9]|20|4\+)){0,9}$/.test(value)) throw new InvalidPropertyQuery();
    if (["min_price", "max_price", "page", "limit"].includes(key)) {
      const n = Number(value);
      if (!/^\d+$/.test(value) || !Number.isSafeInteger(n) || n < (["page", "limit"].includes(key) ? 1 : 0) || (key === "limit" && n > 50)) throw new InvalidPropertyQuery();
      output.set(key, String(n));
    } else output.set(key, value);
  }
  if (output.has("min_price") && output.has("max_price") && Number(output.get("min_price")) > Number(output.get("max_price"))) throw new InvalidPropertyQuery();
  output.sort();
  return output;
}
export function propertyId(value: string): string {
  if (!/^[a-zA-Z0-9_-]{1,100}$/.test(value)) throw new InvalidPropertyQuery();
  return value;
}
