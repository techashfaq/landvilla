import test from "node:test";
import assert from "node:assert/strict";
import { loadComponent, nodes, text } from "./phase21-harness.ts";

function page(meta: () => Promise<unknown>) {
  return loadComponent("app/(public)/city/[city]/page.tsx", "default", {
    "@/lib/public-api": { getPublicApi: () => ({ meta }) },
    "@/lib/seo": { canonicalOrigin: () => null },
    "next/navigation": { notFound: () => { throw new Error("not found"); } },
  });
}
test("city directory uses actual API locality names and safe links", async () => {
  const tree = await page(async () => ({ localities: [{ id: "fixture", slug: "fixture-locality", name_en: "Fixture locality" }] }))({ params: Promise.resolve({ city: "ujjain" }) });
  assert.match(text(tree), /Fixture locality/);
  assert.ok(nodes(tree).some(node => node.props.href === "/city/ujjain/fixture-locality"));
  assert.match(text(tree), /do not imply/);
});
test("city directory handles empty data and backend outage without invented places", async () => {
  const empty = await page(async () => ({ localities: [] }))({ params: Promise.resolve({ city: "ujjain" }) });
  assert.match(text(empty), /No localities/);
  const outage = await page(async () => { throw new Error("private-provider-detail"); })({ params: Promise.resolve({ city: "ujjain" }) });
  assert.match(text(outage), /temporarily unavailable/);
  assert.doesNotMatch(text(outage), /private-provider/);
});
test("unsupported city fails before contacting the API", async () => {
  let calls = 0;
  await assert.rejects(async () => page(async () => { calls++; return {}; })({ params: Promise.resolve({ city: "unsupported" }) }), /not found/);
  assert.equal(calls, 0);
});

test("known locality without inventory shows empty state instead of a dead directory link", async () => {
  const component = loadComponent("app/(public)/city/[city]/[locality]/page.tsx", "default", {
    "@/lib/public-api": { getPublicApi: () => ({ meta: async () => ({ localities: [{ id: "loc_1", slug: "fixture", name_en: "Fixture" }] }), properties: async () => ({ total: 0, items: [] }) }) },
    "next/navigation": { notFound: () => { throw new Error("not found"); } },
  });
  const tree = await component({ params: Promise.resolve({ city: "ujjain", locality: "fixture" }) });
  assert.match(text(tree), /No properties to show yet/);
  assert.ok(nodes(tree).some(node => node.props.href === "/city/ujjain"));
  await assert.rejects(async () => component({ params: Promise.resolve({ city: "ujjain", locality: "unknown" }) }), /not found/);
});
