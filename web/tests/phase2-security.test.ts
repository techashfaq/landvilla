import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { sessionCookie, validSessionCookie } from "../src/lib/session-cookie.ts";
import { readConfig } from "../src/lib/config.ts";
import { forward } from "../src/lib/proxy.ts";
import { health } from "../src/lib/health.ts";
import { verificationEnvironment, copyBuildEntry, assertStandaloneArtifact } from "../scripts/production-build-safety.mjs";

const environment = { CLIENT_IP_MODE:"signed-v1", LANDVILLA_INGRESS_TOKEN:"d".repeat(64), WEB_API_IP_KEY:"e".repeat(64), NODE_ENV: "production", WEB_ORIGIN: "https://landvilla.in", BACKEND_ORIGIN: "http://api:8000", BACKEND_TRANSPORT: "private-http" };
const config = readConfig(environment);
const cookie = "__Host-lv_session=synthetic; Path=/; Secure; HttpOnly; SameSite=Lax";

test("session response rejects conflicting attributes, wrong names and malformed values", () => {
  assert.equal(validSessionCookie(cookie, true), true);
  for (const suffix of ["; SameSite=None", "; Path=/admin", "; Secure=false", "; HttpOnly=no", "; Domain=landvilla.in", "; Max-Age=nan", "; Expires=invalid", "; Partitioned"]) {
    assert.equal(validSessionCookie(cookie + suffix, true), false, suffix);
  }
  for (const value of [cookie.replace("__Host-", "__host-"), cookie.replace("synthetic", '"value"'), cookie.replace("; Secure", ""), cookie.replace("; HttpOnly", "")]) {
    assert.equal(validSessionCookie(value, true), false, value);
  }
});

test("valid logout expiry and cookie flags are retained", () => {
  assert.equal(validSessionCookie("__Host-lv_session=; Path=/; Secure; HttpOnly; SameSite=lax; Max-Age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT", true), true);
  assert.equal(validSessionCookie("lv_dev_session=synthetic; Path=/; HttpOnly; SameSite=Lax", false), true);
});

test("request session parsing rejects duplicate and invalid cookie octets", () => {
  assert.equal(sessionCookie("unrelated=1; __Host-lv_session=synthetic", true), "__Host-lv_session=synthetic");
  for (const raw of ["__Host-lv_session=a; __Host-lv_session=b", "__Host-lv_session=bad value", "__Host-lv_session=bad,value", '__Host-lv_session="quoted"', "__host-lv_session=a"]) {
    assert.equal(sessionCookie(raw, true), null);
  }
});

test("public metadata and legal reads discard request identity and upstream cookies", async () => {
  for (const path of ["/api/meta", "/api/legal/privacy.json", "/api/legal/terms.json"]) {
    const response = await forward(new Request(config.webOrigin + path, { headers: {
      Cookie: "__Host-lv_session=synthetic", "X-CSRF-Token": "synthetic", Origin: config.webOrigin,
    } }), config, async (_url, init) => {
      const headers = new Headers(init?.headers);
      assert.equal(headers.get("cookie"), null);
      assert.equal(headers.get("x-csrf-token"), null);
      assert.equal(headers.get("origin"), config.webOrigin);
      return Response.json({ public: true }, { headers: { "Set-Cookie": cookie } });
    });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("set-cookie"), null);
  }
});

test("private proxy rejects unsafe response cookies and preserves redirects rejection", async () => {
  const request = new Request(config.webOrigin + "/api/auth/me");
  assert.equal((await forward(request, config, async () => Response.json({}, { headers: { "Set-Cookie": cookie + "; SameSite=None" } }))).status, 502);
  assert.equal((await forward(request, config, async () => new Response(null, { status: 302, headers: { Location: "https://attacker.invalid" } }))).status, 502);
});

test("readiness accepts only exact success and has nested timeout headroom", async () => {
  for (const status of [201, 204, 302, 503]) {
    const response = await health(environment, true, async () => new Response(null, { status }));
    assert.equal(response.status, 503);
    assert.deepEqual(await response.json(), { status: "unavailable" });
  }
  const original = AbortSignal.timeout;
  const deadlines: number[] = [];
  try {
    AbortSignal.timeout = (milliseconds: number) => { deadlines.push(milliseconds); return original(milliseconds); };
    assert.equal((await health(environment, true, async () => Response.json({ status: "ready" }))).status, 200);
    assert.deepEqual(deadlines, [7000]);
  } finally { AbortSignal.timeout = original; }
});

test("build environment excludes credentials public secret aliases and Node injection", () => {
  const env = verificationEnvironment({ PATH: "synthetic-bin", MONGO_URL: "synthetic-secret", NEXT_PUBLIC_SECRET: "synthetic", NODE_OPTIONS: "--require=attacker", HTTP_PROXY: "synthetic", NPM_TOKEN: "synthetic" }, "synthetic-temp");
  for (const name of ["MONGO_URL", "NEXT_PUBLIC_SECRET", "NODE_OPTIONS", "HTTP_PROXY", "NPM_TOKEN"]) assert.equal(name in env, false);
  assert.equal(env.PATH, "synthetic-bin");
  assert.equal(env.BACKEND_ORIGIN, "http://api:8000");
  for (const path of [".env", "public/.env.local", "src/nested/.ENV.production"]) assert.equal(copyBuildEntry(path), false);
  assert.equal(copyBuildEntry("src/app/page.tsx"), true);
});

test("standalone completeness check fails without server build metadata or static assets", () => {
  const cache = resolve("../.cache");
  mkdirSync(cache, { recursive: true });
  const stage = mkdtempSync(resolve(cache, "standalone-contract-"));
  try {
    assert.throws(() => assertStandaloneArtifact(stage));
    mkdirSync(resolve(stage, ".next/static"), { recursive: true });
    mkdirSync(resolve(stage, "public"));
    for (const name of ["server.js", "package.json", ".next/BUILD_ID", ".next/routes-manifest.json"]) writeFileSync(resolve(stage, name), "synthetic");
    assert.throws(() => assertStandaloneArtifact(stage));
    writeFileSync(resolve(stage, ".next/static/chunk.js"), "synthetic");
    assert.doesNotThrow(() => assertStandaloneArtifact(stage));
  } finally { rmSync(stage, { recursive: true, force: true }); }
});
