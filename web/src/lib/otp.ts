import type { OtpRequest, Registration } from "./contracts.ts";

export function loginRequest(identifier: string): OtpRequest {
  let normalized = identifier.trim();
  if (normalized.startsWith("+")) {
    normalized = normalized.replace(/[ -]/g, "");
    if (!/^\+[1-9]\d{7,14}$/.test(normalized)) throw new Error("Enter a mobile number with country code, such as +91 followed by ten digits.");
  } else {
    normalized = normalized.toLowerCase();
    if (normalized.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized)) throw new Error("Enter a valid email address.");
  }
  return { identifier: normalized, purpose: "login" };
}
export function registrationRequest(form: FormData): OtpRequest {
  const first_name = String(form.get("first_name") || "").trim();
  const last_name = String(form.get("last_name") || "").trim();
  if (!first_name || !last_name || first_name.length > 60 || last_name.length > 60) throw new Error("First and last name are required (maximum 60 characters each).");
  const email = loginRequest(String(form.get("email") || "")).identifier;
  if (email.startsWith("+")) throw new Error("Registration requires an email address.");
  const mobile = loginRequest(String(form.get("mobile") || "")).identifier;
  if (!mobile.startsWith("+")) throw new Error("Enter your mobile number with country code.");
  const role = String(form.get("account_role") || "");
  if (!["buyer", "owner", "broker", "builder"].includes(role)) throw new Error("Choose an ordinary account type.");
  if (form.get("accept_terms") !== "on" || form.get("accept_privacy") !== "on") throw new Error("Please accept the terms and privacy policy.");
  const registration: Registration = { first_name, last_name, email, mobile, account_role: role as Registration["account_role"], accept_terms: true, accept_privacy: true };
  return { identifier: email, purpose: "register", registration };
}
