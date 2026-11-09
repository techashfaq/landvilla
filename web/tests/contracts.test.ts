import test from "node:test";
import assert from "node:assert/strict";
import { parseChallenge, parseSession, parseStats, parseUser } from "../src/lib/contracts.ts";
import { readConfig } from "../src/lib/config.ts";
import { loginRequest, registrationRequest } from "../src/lib/otp.ts";

test("session contract rejects native token fallback and malformed identities", () => {
  assert.throws(() => parseSession({ session_token: "fixture", csrf_token: "fixture-csrf", user: null, expires_in: 10 }));
  assert.throws(() => parseSession({ csrf_token: "", user: null, expires_in: 10 }));
  assert.throws(() => parseSession({ csrf_token: "fixture-csrf", user: {}, expires_in: 10 }));
  assert.throws(() => parseSession({ csrf_token: "fixture-csrf", user: null, expires_in: 0 }));
  assert.deepEqual(parseSession({ csrf_token: "fixture-csrf", user: null, expires_in: 10 }), { csrf_token: "fixture-csrf", user: null, expires_in: 10 });
});
test("public user projection never retains internal metadata", () => {
  const user = parseUser({ user_id: "fixture-user", name: "Test", email: "test@example.test", role: "buyer", password_digest: "fixture", google_sub: "fixture" });
  assert.deepEqual(Object.keys(user).sort(), ["email", "name", "role", "user_id"]);
});
test("dashboard counts reject invented/malformed values and allow real zero", () => {
  assert.throws(() => parseStats({ pending_listings: 3 }));
  assert.throws(() => parseStats({ pending_listings: -1, pending_brokers: 0, open_reports: 0, paid_orders: 0 }));
  assert.equal(parseStats({ pending_listings: 0, pending_brokers: 0, open_reports: 0, paid_orders: 0 }).pending_listings, 0);
});
test("challenge parser validates identifiers and never reflects provider content", () => {
  assert.throws(() => parseChallenge({ challenge_id: "short" }));
  assert.equal(parseChallenge({ challenge_id: "fixture-challenge-00000", expires_in: 300, resend_after: 60, message: "fixture-private-provider-content" }).message, "If eligible, a verification code has been sent.");
});
test("OTP login normalizes identifiers; malformed contacts rejected", () => {
  assert.equal(loginRequest("  TEST@Example.test ").identifier, "test@example.test");
  assert.equal(loginRequest("+91 90000-00000").identifier, "+919000000000");
  assert.throws(() => loginRequest("not-an-email"));
  assert.throws(() => loginRequest("+1"));
});
function registration() {
  const form = new FormData();
  for (const [key, value] of Object.entries({ first_name: "Test", last_name: "Owner", email: "test@example.test", mobile: "+919000000000", account_role: "owner", accept_terms: "on", accept_privacy: "on" })) form.set(key, value);
  return form;
}
test("registration enforces required consents/ordinary roles; ignores privileged fields", () => {
  const form = registration(); form.set("role", "admin");
  const payload = registrationRequest(form);
  assert.equal(payload.purpose, "register"); assert.equal(payload.registration?.account_role, "owner");
  assert.ok(!("role" in payload.registration!));
  form.set("account_role", "admin"); assert.throws(() => registrationRequest(form));
  form.set("account_role", "buyer"); form.delete("accept_privacy"); assert.throws(() => registrationRequest(form));
});
test("origin config rejects production HTTP, credentials, paths, loops and absent settings", () => {
  assert.equal(readConfig({}).webOrigin, "http://localhost:19006");
  for (const env of [
    { NODE_ENV: "production" },
    { BACKEND_ORIGIN: "http://example.test" },
    { BACKEND_ORIGIN: "https://user:pass@example.test" },
    { BACKEND_ORIGIN: "https://example.test/api" },
    { BACKEND_ORIGIN: "http://localhost:19006" },
    { NODE_ENV: "production", BACKEND_ORIGIN: "https://api.example.test", WEB_ORIGIN: "http://localhost:19006" },
  ]) assert.throws(() => readConfig(env));
  assert.equal(readConfig({ NODE_ENV: "production", BACKEND_ORIGIN: "https://api.example.test", WEB_ORIGIN: "https://example.test" }).production, true);
});
