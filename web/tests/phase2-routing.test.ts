import test from "node:test";
import assert from "node:assert/strict";
import { accountPath } from "../src/lib/account-routes.ts";
import { canonicalOrigin } from "../src/lib/seo.ts";
import { propertyHref } from "../src/lib/property-links.ts";
import { publicImage } from "../src/lib/property-contracts.ts";
test("only listing pagination is accepted on account routes", () => {
  assert.equal(accountPath("GET", "/api/listings/mine?page=2&limit=20"), "/api/listings/mine?limit=20&page=2");
  for (const path of ["/api/listings/mine?token=x", "/api/listings/mine?page=2&page=3", "/api/listings/mine?limit=101", "/api/saved?page=1", "/api/listings/mine?page=0", "https://evil.test/api/saved"]) assert.throws(() => accountPath("GET", path));
});
test("canonical origins require explicit safe configuration", () => {
  assert.equal(canonicalOrigin({}), null); assert.equal(canonicalOrigin({WEB_ORIGIN:"https://example.test"}), "https://example.test");
  assert.equal(canonicalOrigin({WEB_ORIGIN:"http://localhost:19006",NODE_ENV:"production"}),null);
  assert.equal(canonicalOrigin({WEB_ORIGIN:"https://user:password@example.test"}),null);
});
test("property URLs preserve stable IDs and reviewed colour-space image queries", () => {
  assert.equal(propertyHref({id:"prop_test",title:"A place / home"}),"/property/a-place-home~prop_test");
  assert.ok(publicImage("https://images.unsplash.com/photo-test?crop=entropy&cs=tinysrgb&fm=jpg&q=80&w=800"));
});
