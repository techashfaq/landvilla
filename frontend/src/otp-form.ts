export function normalizeIdentifier(value: string) {
  const trimmed = value.trim();
  return trimmed.includes("@") ? trimmed.toLowerCase() : trimmed.replace(/[ -]/g, "");
}
export function validIdentifier(value: string) {
  const normalized = normalizeIdentifier(value);
  return normalized.length <= 254 && (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized) || /^\+[1-9][0-9]{7,14}$/.test(normalized));
}
export function registrationValid(first: string, last: string, email: string, mobile: string, role: string, terms: boolean, privacy: boolean) {
  return !!first.trim() && first.trim().length <= 60 && !!last.trim() && last.trim().length <= 60 &&
    normalizeIdentifier(email).includes("@") && validIdentifier(email) &&
    /^\+[1-9][0-9]{7,14}$/.test(normalizeIdentifier(mobile)) &&
    ["buyer", "owner", "broker", "builder"].includes(role) && terms && privacy;
}
