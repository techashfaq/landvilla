import test from "node:test";
import assert from "node:assert/strict";
import { checkAdmin, readAdminStats } from "../src/lib/admin-access.ts";
const user = { user_id: "fixture", email: "test@example.test", name: "Test", role: "buyer" };
test("admin access denies ordinary roles, expired sessions and malformed profiles", async () => {
  assert.equal((await checkAdmin(async () => ({ status: 200, data: user }))).kind, "denied");
  assert.equal((await checkAdmin(async () => ({ status: 401, data: null }))).kind, "signed-out");
  assert.equal((await checkAdmin(async () => ({ status: 200, data: {} }))).kind, "unavailable");
  assert.equal((await checkAdmin(async () => { throw new Error("fixture outage"); })).kind, "unavailable");
});
test("non-admin callers never request dashboard stats", async () => {
  const paths: string[] = [];
  assert.equal(await readAdminStats(async path => { paths.push(path); return { status: 200, data: user }; }), null);
  assert.deepEqual(paths, ["/api/auth/me"]);
});
test("stats remain subject to backend authorization and never default to fake zeroes", async () => {
  assert.equal(await readAdminStats(async path => path.endsWith("me") ? { status: 200, data: { ...user, role: "admin" } } : { status: 403, data: null }), null);
  const stats = { pending_listings: 3, pending_brokers: 1, open_reports: 0, paid_orders: 2 };
  assert.deepEqual(await readAdminStats(async path => ({ status: 200, data: path.endsWith("me") ? { ...user, role: "admin" } : stats })), stats);
});
