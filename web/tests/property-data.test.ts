import test from "node:test";
import assert from "node:assert/strict";
import { propertyQuery } from "../src/lib/property-query.ts";
import { parseMeta, parseProperty, parsePropertyPage, publicImage } from "../src/lib/property-contracts.ts";
import { publicApi, PublicApiError } from "../src/lib/public-transport.ts";
import { readConfig } from "../src/lib/config.ts";

const fixture = { id: "test_property", title_en: "Fictional test property", purpose: "buy", segment: "residential", type: "apartment", price: 1000, area_sqft: 100, is_demo: true };
test("property query permits supported combinations and canonical pagination", () => {
  const query = propertyQuery(new URLSearchParams("purpose=buy&locality=test-locality,test_second&bhk=2,4%2B&min_price=0&max_price=5000&page=02&limit=5&sort=price_asc&q=hello"));
  assert.equal(query.get("page"), "2"); assert.equal(query.get("bhk"), "2,4+"); assert.equal(query.get("q"), "hello");
});
test("unsupported, duplicate, credential and invalid query values fail closed", () => {
  for (const query of ["token=secret", "city=indore", "area=100", "q=a&q=b", "purpose=sell", "page=0", "page=1.5", "limit=51", "sort=relevance", "min_price=200&max_price=100", "bhk=2,garbage", "locality=../private", "q=%00", "max_price=9007199254740992"]) assert.throws(() => propertyQuery(new URLSearchParams(query)), query);
});
test("public projection excludes private fields and retains fictional designation", () => {
  const projected = parseProperty({ ...fixture, email: "private", owner_user_id: "private", is_saved: true, _id: "private", moderation: { reason: "private" }, documents: ["private"], mobile: "private", google_sub: "private" });
  assert.equal(projected.is_demo, true); assert.ok(!JSON.stringify(projected).includes("private")); assert.ok(!("is_saved" in projected));
});
test("featured status requires a valid future expiry; invalid public records fail", () => {
  assert.equal(parseProperty({ ...fixture, featured: true }).featured, false);
  assert.equal(parseProperty({ ...fixture, featured: true, featured_until: "2000-01-01" }).featured, false);
  assert.equal(parseProperty({ ...fixture, featured: true, featured_until: "2040-01-01" }, 0).featured, true);
  assert.throws(() => parseProperty({ ...fixture, price: NaN }));
  assert.throws(() => parseProperty({ ...fixture, is_demo: "true" }));
});
test("image URLs reject credentials, private query tokens and unreviewed hosts", () => {
  assert.equal(publicImage("/api/files/file_test"), "/api/files/file_test");
  assert.ok(publicImage("https://images.unsplash.com/photo-test?w=800&auto=format"));
  for (const value of ["//evil.test/image", "javascript:alert(1)", "/api/files/a?token=private", "https://user:pass@images.unsplash.com/image", "https://images.unsplash.com/image?token=private", "https://unreviewed.test/image"]) assert.equal(publicImage(value), null);
});
test("pagination validates response instead of inventing counts", () => {
  assert.equal(parsePropertyPage({ items: [fixture], total: 2, page: 2, limit: 1 }).page, 2);
  assert.throws(() => parsePropertyPage({ items: [fixture], total: 0, page: 1, limit: 20 }));
});
test("metadata projects only active real locality identifiers", () => {
  const place = { id: "test_city", slug: "ujjain", name_en: "Ujjain", secret: "private" };
  const meta = parseMeta({ city: place, zones: [], localities: [{ ...place, is_active: true }, { ...place, is_active: false }], categories: [], property_types: [], amenities: [] });
  assert.equal(meta.localities.length, 1); assert.ok(!JSON.stringify(meta).includes("private"));
});
test("anonymous transport never forwards identity or caches personalized results", async () => {
  let calls = 0;
  const api = publicApi(readConfig({}), async (url, init) => {
    calls++; assert.equal(String(url), "http://127.0.0.1:8000/api/properties?limit=5&purpose=buy");
    assert.equal(init?.credentials, "omit"); assert.equal(init?.cache, "no-store"); assert.equal(init?.redirect, "manual");
    const headers = new Headers(init?.headers); assert.equal(headers.get("cookie"), null); assert.equal(headers.get("authorization"), null);
    return Response.json({ items: [fixture], total: 1, page: 1, limit: 5 });
  });
  assert.equal((await api.properties(new URLSearchParams("purpose=buy&limit=5"))).items[0]?.is_demo, true);
  assert.throws(() => api.properties(new URLSearchParams("token=private"))); assert.equal(calls, 1);
});
test("unknown IDs, redirects, malformed data and provider errors are safe", async () => {
  for (const status of [302, 404, 500]) {
    const api = publicApi(readConfig({}), async () => new Response("private upstream details", { status }));
    await assert.rejects(api.property("unknown"), error => error instanceof PublicApiError && !error.message.includes("private"));
    assert.throws(() => api.property("../auth/me"));
  }
  const api = publicApi(readConfig({}), async () => Response.json({ private: "bad-schema" }));
  await assert.rejects(api.meta(), PublicApiError);
});
