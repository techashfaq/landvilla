import test from "node:test";
import assert from "node:assert/strict";
import { adminPath, adminRoute, moderationBody, moderationActions } from "../src/lib/admin-routes.ts";
import { readAdminRecords, projectAdminRecord } from "../src/lib/admin-resources.ts";
import { ApiError, BrowserClient } from "../src/lib/browser-client.ts";

const user = { user_id: "admin_fixture", name: "Fixture", email: "fixture@example.test", role: "admin" };
const session = (role = "admin") => ({ user: { ...user, role }, csrf_token: "fixture-csrf", expires_in: 300 });

test("admin policy permits only implemented reads and reviewed moderation actions", () => {
  assert.equal(adminPath("GET", "/api/admin/listings?status=pending_review"), "/api/admin/listings?status=pending_review");
  assert.equal(adminPath("POST", "/api/admin/brokers/fixture/approve"), "/api/admin/brokers/fixture/approve");
  for (const path of ["/api/admin/brokers?role=admin", "/api/admin/listings?status=active&status=active", "/api/admin/brokers?token=fixture", "/api/admin/listings/%2e%2e/approve", "/api/admin/listings?status=active#secret"]) assert.throws(() => adminPath("GET", path));
  for (const path of ["/api/admin/staff/fixture/promote", "/api/admin/brokers/fixture/delete", "/api/admin/brokers/fixture/approve?x=1"]) assert.equal(adminRoute("POST", path), false);
});
test("moderation requires bounded reasons and respects visible transitions and self-review", () => {
  assert.deepEqual(moderationBody("reject", "  Needs ownership proof  "), { note: "Needs ownership proof" });
  for (const note of ["", "x", "x".repeat(1001)]) assert.throws(() => moderationBody("reject", note));
  assert.deepEqual(moderationActions("brokers", "approved", false), ["suspend"]);
  assert.deepEqual(moderationActions("brokers", "pending", true), []);
  assert.deepEqual(moderationActions("listings", "rejected", false), []);
});
test("each admin resource read checks role independently before fetching records", async () => {
  for (const role of ["buyer", "owner", "broker"]) {
    const paths: string[] = [];
    const result = await readAdminRecords(async path => { paths.push(path); return { status: 200, data: { ...user, role } }; }, "properties");
    assert.equal(result.kind, "denied"); assert.deepEqual(paths, ["/api/auth/me"]);
  }
  const result = await readAdminRecords(async () => ({ status: 401, data: null }), "brokers");
  assert.equal(result.kind, "signed-out");
});
test("admin resources fail closed on backend denial, malformed records and unknown filters", async () => {
  for (const response of [{ status: 403, data: null }, { status: 200, data: { items: [{}] } }, { status: 500, data: { private: "fixture" } }]) {
    const result = await readAdminRecords(async path => path === "/api/auth/me" ? { status: 200, data: user } : response, "properties");
    assert.notEqual(result.kind, "ready"); assert.deepEqual(result.items, []);
  }
  const paths: string[] = [];
  await readAdminRecords(async path => { paths.push(path); return { status: 200, data: user }; }, "properties", "arbitrary");
  assert.deepEqual(paths, ["/api/auth/me"]);
});
test("admin projection discards unapproved fields and rejects external document URLs", () => {
  const record = projectAdminRecord("brokers", { user_id: "fixture", full_name: "Broker fixture", email: "fixture@example.test", status: "pending", password_hash: "private", otp: "private", documents: [{ id: "doc_1", name: "Document", url: "https://untrusted.test/private" }, { id: "../secret", name: "Invalid" }] });
  assert.equal(JSON.stringify(record).includes("private"), false);
  assert.deepEqual(record.documents, [{ id: "doc_1", name: "Document" }]);
});
test("admin resource responses are projected only after authorization", async () => {
  const result = await readAdminRecords(async path => ({ status: 200, data: path === "/api/auth/me" ? user : { items: [{ id: "p1", title_en: "Fixture", listing_status: "pending_review", owner: { user_id: "owner" }, secret: "private" }] } }), "properties", "pending_review");
  assert.equal(result.kind, "ready"); assert.equal(result.items.length, 1); assert.equal(JSON.stringify(result).includes("private"), false);
});
test("operational modules call their explicit authorized endpoints", async () => {
  for (const section of ["users", "staff", "cms", "enquiries"] as const) {
    const paths: string[] = [];
    const result = await readAdminRecords(async path => { paths.push(path); return { status: 200, data: path === "/api/auth/me" ? user : { items: [], total: 0 } }; }, section);
    assert.equal(result.kind, "ready"); assert.equal(paths.length, 2);
    assert.ok(paths[1]!.startsWith(`/api/admin/${section}?`));
  }
});

test("admin browser mutations require current admin session and CSRF", async () => {
  const calls: string[] = [];
  const client = new BrowserClient(async (path, init) => {
    calls.push(String(path));
    if (String(path).includes("bootstrap")) return Response.json(session());
    assert.equal(init?.method, "POST"); assert.equal(init?.credentials, "same-origin");
    assert.equal(new Headers(init?.headers).get("X-CSRF-Token"), "fixture-csrf");
    assert.equal(new Headers(init?.headers).has("Authorization"), false);
    assert.equal(init?.body, JSON.stringify({ note: "Reviewed proof" }));
    return Response.json({ id: "p1", listing_status: "active" });
  });
  await client.admin("/api/admin/listings/p1/approve", "Reviewed proof");
  assert.equal(calls.length, 2);
});
test("ordinary browser roles and broker self-approval cannot send moderation writes", async () => {
  for (const role of ["buyer", "admin"]) {
    let writes = 0;
    const client = new BrowserClient(async path => { if (String(path).includes("bootstrap")) return Response.json(session(role)); writes++; return Response.json({}); });
    await assert.rejects(client.admin("/api/admin/brokers/admin_fixture/approve", ""));
    assert.equal(writes, 0);
  }
});
test("session invalidation rejects late administrative success", async () => {
  let release!: (response: Response) => void;
  const client = new BrowserClient(async path => String(path).includes("bootstrap") ? Response.json(session()) : new Promise<Response>(resolve => { release = resolve; }));
  await client.bootstrap();
  const pending = client.admin("/api/admin/listings/p1/approve", "");
  const rejected = assert.rejects(pending, error => error instanceof ApiError && error.status === 409);
  client.invalidate(); release(Response.json({ id: "p1", listing_status: "active" })); await rejected;
  assert.equal(client.snapshot().session, null);
});

test("admin decisions require matching backend confirmation", async () => {
  for (const data of [{}, { id: "wrong", listing_status: "active" }, { id: "p1", listing_status: "pending_review" }]) {
    const client = new BrowserClient(async path => Response.json(String(path).includes("bootstrap") ? session() : data));
    await assert.rejects(client.admin("/api/admin/listings/p1/approve", ""), error => error instanceof ApiError && error.status === 502);
  }
});

test("server pagination validates keys, bounds and status values", () => {
  assert.equal(adminPath("GET", "/api/admin/listings?q=house%20near&page=2&limit=20"), "/api/admin/listings?q=house+near&page=2&limit=20");
  for (const query of ["page=0", "limit=100000", "q=a&q=b", "role=admin", "status=arbitrary"]) assert.throws(() => adminPath("GET", "/api/admin/users?" + query));
  assert.deepEqual(moderationActions("listings", "suspended", false), ["reactivate"]);
  assert.equal(adminRoute("POST", "/api/admin/payments/p1/paid"), false);
});
test("configuration writes require admin session and retain CSRF", async () => {
  let writes = 0;
  const client = new BrowserClient(async (path, init) => {
    if (String(path).includes("bootstrap")) return Response.json(session());
    writes++; assert.equal(new Headers(init?.headers).get("X-CSRF-Token"), "fixture-csrf");
    return Response.json({ id: "plan1" });
  });
  await client.adminOperation("/api/admin/featured-plans/plan1", "PUT", { price_inr: 500 });
  assert.equal(writes, 1);
  await assert.rejects(client.adminOperation("/api/admin/payments/p1/paid", "POST", {}));
});

test("audited enquiry detail requires an administrator and cannot accept arbitrary paths", async () => {
  const client = new BrowserClient(async path => Response.json(String(path).includes("bootstrap") ? session("buyer") : { id: "e1" }));
  await assert.rejects(client.adminDetail("/api/admin/enquiries/e1"), error => error instanceof ApiError && error.status === 403);
  assert.equal(adminRoute("GET", "/api/admin/enquiries/e1"), true);
  assert.equal(adminRoute("GET", "/api/admin/enquiries/e1?token=secret"), false);
});

test("payment inspection remains available while refunds are disabled", () => {
  assert.equal(adminRoute("GET", "/api/admin/payments/pay1"), true);
  assert.equal(adminRoute("POST", "/api/admin/payments/pay1/refund"), false);
  for (const action of ["paid", "success", "activate", "settle"]) assert.equal(adminRoute("POST", `/api/admin/payments/pay1/${action}`), false);
});
