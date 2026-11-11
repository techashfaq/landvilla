import test from "node:test";
import assert from "node:assert/strict";
import { copyPropertyLink } from "../src/lib/share-link.ts";

const location = { origin: "https://example.test", pathname: "/property/fixture", search: "?token=synthetic", hash: "#private" };
test("sharing tolerates missing clipboard and permission denial", async () => {
  assert.match(await copyPropertyLink(location), /browser/);
  assert.match(await copyPropertyLink(location, { writeText: async () => { throw new Error("permission denied"); } }), /browser/);
});
test("sharing copies only public origin and pathname", async () => {
  let copied = "";
  assert.equal(await copyPropertyLink(location, { writeText: async value => { copied = value; } }), "Property link copied.");
  assert.equal(copied, "https://example.test/property/fixture");
});
