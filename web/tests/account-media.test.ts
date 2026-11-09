import test from "node:test";
import assert from "node:assert/strict";
import { forward } from "../src/lib/proxy.ts";
import { accountRoute } from "../src/lib/account-routes.ts";
import { validateUpload } from "../src/lib/media.ts";
import { listingInput } from "../src/lib/listing-form.ts";
import { BrowserClient } from "../src/lib/browser-client.ts";
const config = { backendOrigin: "http://127.0.0.1:8000", webOrigin: "http://localhost:19006", production: false };
const headers = { Origin: config.webOrigin, "Content-Type": "application/json", "X-CSRF-Token": "test-csrf", Cookie: "lv_dev_session=test-cookie" };
test("customer routes never permit staff, publication, payments or arbitrary paths", () => {
  assert.ok(accountRoute("POST", "/api/saved/test_id")); assert.ok(accountRoute("PUT", "/api/listings/test_id"));
  for (const path of ["/api/admin/listings/test/approve", "/api/payments/featured/order", "/api/listings/test/publish", "/api/auth/session"]) assert.equal(accountRoute("POST", path), false);
});
test("PATCH PUT DELETE require origin and CSRF exactly as POST does", async () => {
  for (const [method, path] of [["PATCH", "/api/me/profile"], ["PUT", "/api/listings/test"], ["DELETE", "/api/saved/test"]]) {
    const response = await forward(new Request(config.webOrigin + path, { method, headers: { "Content-Type": "application/json", Origin: config.webOrigin }, body: "{}" }), config, async () => { throw new Error("must not forward"); });
    assert.equal(response.status, 403);
  }
});
test("ownership, consent and moderation remain authoritative backend decisions", async () => {
  for (const [method, path, body] of [["POST", "/api/enquiries", { property_id: "test", share_phone_consent: false }], ["PUT", "/api/listings/another_owner", {}], ["GET", "/api/saved", undefined]] as const) {
    const response = await forward(new Request(config.webOrigin + path, { method, headers, body: method === "GET" ? undefined : JSON.stringify(body) }), config, async (_, init) => {
      if (method === "POST") assert.equal(JSON.parse(String(init?.body)).share_phone_consent, false);
      return Response.json({ detail: "Access denied" }, { status: 403 });
    }); assert.equal(response.status, 403);
  }
});
function upload(kind = "property_photo", bytes = new Uint8Array([255,216,255,0]), name = "test.jpg", type = "image/jpeg") { const form = new FormData(); form.set("kind", kind); form.set("file", new File([bytes], name, { type })); return form; }
test("upload enforces kind, extension, MIME, signature and size", async () => {
  await validateUpload(upload());
  for (const form of [upload("other"), upload("property_photo", new Uint8Array([0])), upload("property_photo", new Uint8Array([255,216,255]), "bad.svg"), upload("property_photo", new Uint8Array([37,80,68,70,45]), "file.pdf", "application/pdf"), upload("broker_doc", new Uint8Array(10*1024*1024+1))]) await assert.rejects(validateUpload(form));
});
test("multipart proxy validates before sending and preserves browser guards", async () => {
  const request = new Request(config.webOrigin + "/api/uploads", { method: "POST", headers: { Origin: config.webOrigin, "X-CSRF-Token": "test", Cookie: "lv_dev_session=test" }, body: upload() });
  const result = await forward(request, config, async (_, init) => { assert.ok(init?.body instanceof FormData); assert.equal(new Headers(init.headers).get("content-type"), null); assert.equal(new Headers(init.headers).get("x-lv-client"), "web"); return Response.json({ id: "test_file", kind: "property_photo" }); });
  assert.equal(result.status, 200);
});
test("private file denial passes through; successful files are never publicly cached", async () => {
  const request = () => new Request(config.webOrigin + "/api/files/test", { headers: { Cookie: "lv_dev_session=test" } });
  assert.equal((await forward(request(), config, async () => Response.json({ detail: "Denied" }, { status: 403 }))).status, 403);
  const result = await forward(request(), config, async () => new Response("test-pdf", { headers: { "Content-Type": "application/pdf", "Cache-Control": "public,max-age=86400" } }));
  assert.equal(result.headers.get("cache-control"), "private, no-store"); assert.match(result.headers.get("content-disposition")!, /attachment/);
  const denied = await forward(new Request(config.webOrigin + "/api/files/test?token=forbidden"), config, async () => { throw new Error(); }); assert.equal(denied.status, 400);
});
test("listing body never forwards owner IDs, role grants or publication status", () => {
  const form = new FormData(); for (const [key,value] of Object.entries({ title_en: "Test listing", description_en: "Fictional test description long enough.", purpose: "buy", posted_as: "owner", price: "1000", area_sqft: "100", declaration: "on", listing_status: "active", owner_user_id: "another", role: "admin" })) form.set(key,value);
  const result = listingInput(form,["test_photo"]); assert.ok(!("listing_status" in result)); assert.ok(!("owner_user_id" in result)); assert.ok(!("role" in result)); assert.equal(result.owner_declaration_accepted,true);
  form.delete("declaration"); assert.throws(()=>listingInput(form,["test_photo"]));
});
test("account adapter uses current CSRF; anonymous state cannot mutate saved properties", async () => {
  let calls=0; const client = new BrowserClient(async () => { calls++; return Response.json({user:null,csrf_token:"test",expires_in:900}); });
  await assert.rejects(client.account("/api/saved/test", "POST", {})); assert.equal(calls,1);
  await assert.rejects(client.account("/api/admin/anything", "POST", {})); assert.equal(calls,1);
});
