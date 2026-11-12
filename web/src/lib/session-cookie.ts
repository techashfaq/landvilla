// Cookie names are case-sensitive; values use the RFC 6265 cookie-octet set.
const cookieValue = /^[\x21\x23-\x2b\x2d-\x3a\x3c-\x5b\x5d-\x7e]*$/;

export function sessionCookie(raw: string | null, secure: boolean): string | null {
  const name = secure ? "__Host-lv_session" : "lv_dev_session";
  const matches = (raw || "").split(";").map(x => x.trim()).filter(x => x.startsWith(name + "="));
  if (matches.length !== 1 || !cookieValue.test(matches[0]!.slice(name.length + 1))) return null;
  return matches[0]!;
}

export function validSessionCookie(header: string, secure: boolean): boolean {
  const [pair, ...parts] = header.split(";").map(part => part.trim());
  const name = secure ? "__Host-lv_session" : "lv_dev_session";
  if (!pair?.startsWith(name + "=")) return false;
  const value = pair.slice(name.length + 1);
  // Starlette's delete_cookie serializes the empty value as two quotes.
  // Accept only explicit deletion below, never a quoted authentication token.
  const quotedEmpty = value === '""';
  if (!quotedEmpty && !cookieValue.test(value)) return false;
  const attributes = new Map<string, string | null>();
  for (const part of parts) {
    const equal = part.indexOf("=");
    const key = (equal < 0 ? part : part.slice(0, equal)).trim().toLowerCase();
    const value = equal < 0 ? null : part.slice(equal + 1).trim();
    // A later duplicate can override a previously validated browser attribute.
    if (attributes.has(key) || !["httponly", "secure", "path", "samesite", "max-age", "expires"].includes(key)) return false;
    attributes.set(key, value);
  }
  if (attributes.get("httponly") !== null || attributes.get("path") !== "/" || attributes.get("samesite")?.toLowerCase() !== "lax") return false;
  if ((secure || attributes.has("secure")) && attributes.get("secure") !== null) return false;
  const age = attributes.get("max-age");
  if (quotedEmpty && age !== "0") return false;
  if (attributes.has("max-age") && (age === null || !/^-?\d+$/.test(age!) || !Number.isSafeInteger(Number(age)))) return false;
  const expires = attributes.get("expires");
  if (attributes.has("expires") && (expires === null || !Number.isFinite(Date.parse(expires!)))) return false;
  return true;
}
