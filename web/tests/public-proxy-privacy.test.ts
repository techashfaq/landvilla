import test from "node:test";
import assert from "node:assert/strict";
import { forward } from "../src/lib/proxy.ts";
const config = { backendOrigin: "http://127.0.0.1:8000", webOrigin: "http://localhost:19006", production: false };
const fixture = { id: "fixture", title_en: "Fixture", purpose: "buy", segment: "residential", type: "apartment", price: 100, area_sqft: 100, is_demo: true };
test("public proxy strips private fields and never forwards a session or rotates cookies", async () => {
  for (const path of ["/api/properties", "/api/properties/fixture"]) {
    const response = await forward(new Request(config.webOrigin + path, { headers: { Cookie: "lv_dev_session=synthetic", "X-CSRF-Token": "synthetic" } }), config, async (_url, init) => {
      const headers = new Headers(init?.headers);
      assert.equal(headers.has("cookie"), false); assert.equal(headers.has("x-csrf-token"), false);
      const record = { ...fixture, owner_user_id: "private", email: "private", mobile: "private", documents: ["private"], moderation: { note: "private" }, posted_by_name: "private", address: "private", future_secret: "private" };
      return Response.json(path.endsWith("fixture") ? record : { items: [record], total: 1, page: 1, limit: 20 }, { headers: { "Set-Cookie": "lv_dev_session=unexpected" } });
    });
    assert.equal(response.status, 200); assert.equal(response.headers.has("set-cookie"), false);
    const text = await response.text(); assert.doesNotMatch(text, /private|unexpected/); assert.match(text, /title_en/);
  }
});
test("public proxy fails closed on malformed data and sanitizes upstream errors", async () => {
  const request = new Request(config.webOrigin + "/api/properties");
  for (const upstream of [Response.json({ items: [{}] }), new Response("not-json", { headers: { "Content-Type": "application/json" } })]) {
    assert.equal((await forward(request, config, async () => upstream)).status, 502);
  }
  const response = await forward(request, config, async () => Response.json({ detail: "private-diagnostic" }, { status: 400 }));
  assert.equal(response.status, 400); assert.doesNotMatch(await response.text(), /private-diagnostic/);
});
test("admin proxy requires origin and CSRF and preserves backend denial", async () => {
  const path = config.webOrigin + "/api/admin/listings/fixture/approve";
  let calls = 0;
  const transport: typeof fetch = async () => { calls++; return Response.json({ detail: "Forbidden" }, { status: 403 }); };
  assert.equal((await forward(new Request(path, { method: "POST" }), config, transport)).status, 403);
  assert.equal(calls, 0);
  assert.equal((await forward(new Request(path, { method: "POST", headers: { Origin: config.webOrigin, "X-CSRF-Token": "synthetic", "Content-Type": "application/json" }, body: "{}" }), config, transport)).status, 403);
  assert.equal(calls, 1);
});
