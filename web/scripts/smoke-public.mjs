/** Explicit opt-in GET smoke against existing loopback services. Never runs in npm test. */
import assert from "node:assert/strict";
const base = "http://localhost:19006";
const checks = [
  ["/", 200], ["/properties", 200], ["/buy", 200], ["/rent", 200],
  ["/city/ujjain", 200], ["/city/unsupported-audit-city", 404],
  ["/city/ujjain/nonexistent-audit-locality", 404], ["/property/nonexistent_audit_property", 404],
  ["/unknown-landvilla-audit-route", 404], ["/about", 200], ["/contact", 200], ["/faq", 200],
  ["/legal/privacy", 200], ["/legal/terms", 200], ["/robots.txt", 200], ["/sitemap.xml", 200], ["/login", 200],
  ["/api/properties?limit=1", 200], ["/api/properties?invalid=1", 400],
  ["/api/properties?purpose=buy&purpose=rent", 400], ["/api/properties?min_price=900&max_price=100", 400],
  ["/api/auth/me", 401], ["/api/admin/stats", 401],
  ["/api/admin/listings?status=pending_review", 401], ["/api/admin/brokers?status=pending", 401], ["/api/admin/payments", 401],
];
let failed = 0;
for (const [path, expected] of checks) {
  try {
    const response = await fetch(base + path, { redirect: "manual", credentials: "omit", signal: AbortSignal.timeout(20000) });
    assert.equal(response.status, expected);
    await response.body?.cancel();
    console.log(`PASS ${path} ${response.status}`);
  } catch { failed++; console.log(`FAIL ${path} expected ${expected}`); }
}
console.log(`${checks.length - failed}/${checks.length} HTTP checks passed; ${failed} failed. GET only; no authentication or provider workflow verified.`);
process.exitCode = failed ? 1 : 0;
