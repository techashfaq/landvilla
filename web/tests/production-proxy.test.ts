import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { readConfig } from "../src/lib/config.ts";
import { backendHeaders } from "../src/lib/backend-headers.ts";
import { forward } from "../src/lib/proxy.ts";
import { publicApi } from "../src/lib/public-transport.ts";
import { health } from "../src/lib/health.ts";

const environment = { CLIENT_IP_MODE:"signed-v1", LANDVILLA_INGRESS_TOKEN:"d".repeat(64), WEB_API_IP_KEY:"e".repeat(64), NODE_ENV: "production", WEB_ORIGIN: "https://landvilla.in", BACKEND_ORIGIN: "http://api:8000", BACKEND_TRANSPORT: "private-http" };
const config = readConfig(environment);

test("production public origin is mandatory and always HTTPS", () => {
  for (const WEB_ORIGIN of [undefined, "", "http://landvilla.in", "http://localhost:3000", "http://api:8000", "https://user:password@landvilla.in", "https://landvilla.in/path", "https://landvilla.in?x=1", "https://landvilla.in#x"]) {
    assert.throws(() => readConfig({ ...environment, WEB_ORIGIN }));
  }
  assert.equal(config.webOrigin, "https://landvilla.in");
});

test("internal HTTP is an explicit exception for the exact Docker service only", () => {
  assert.equal(config.backendOrigin, "http://api:8000");
  assert.throws(() => readConfig({ ...environment, BACKEND_TRANSPORT: undefined }));
  assert.throws(() => readConfig({ ...environment, BACKEND_TRANSPORT: "http" }));
  for (const BACKEND_ORIGIN of [undefined, "http://evil.example:8000", "http://api.evil.example:8000", "http://api.:8000", "http://api:8001", "http://api", "http://api:8000/", "http://API:8000", "http://user:password@api:8000", "http://api:8000/path", "http://api:8000?x=1", "http://api:8000#x", "http://10.0.0.1:8000", "http://127.0.0.1:8000", "http://[::1]:8000", "http://169.254.169.254"]) {
    assert.throws(() => readConfig({ ...environment, BACKEND_ORIGIN }), BACKEND_ORIGIN);
  }
  assert.throws(() => readConfig({ ...environment, BACKEND_TRANSPORT: "https" }));
  assert.equal(readConfig({ ...environment, BACKEND_TRANSPORT: undefined, BACKEND_ORIGIN: "https://api.example.test" }).backendOrigin, "https://api.example.test");
});

test("production proxy replaces all spoofed forwarding fields while preserving browser security context", async () => {
  const request = new Request(config.webOrigin + "/api/auth/otp/request", { method: "POST", headers: {
    Origin: config.webOrigin, Referer: config.webOrigin + "/account", "Content-Type": "application/json", "X-CSRF-Token": "synthetic-csrf",
    Cookie: "tracking=synthetic; __Host-lv_session=synthetic-session", "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors",
    Forwarded: "for=1.2.3.4;host=evil.example;proto=http", "X-Forwarded-Proto": "http,https", "X-Forwarded-For": "1.2.3.4", "X-Forwarded-Host": "evil.example", "X-Forwarded-Port": "80", "X-Real-IP": "1.2.3.4", Host: "evil.example",
  }, body: "{}" });
  let calls = 0;
  const response = await forward(request, config, async (url, init) => {
    calls++;
    assert.equal(url, "http://api:8000/api/auth/otp/request");
    const headers = new Headers(init?.headers);
    assert.equal(headers.get("x-forwarded-proto"), "https");
    for (const name of ["forwarded", "x-forwarded-for", "x-forwarded-host", "x-forwarded-port", "x-real-ip", "host"]) assert.equal(headers.get(name), null, name);
    assert.equal(headers.get("origin"), config.webOrigin);
    assert.equal(headers.get("referer"), config.webOrigin + "/account");
    assert.equal(headers.get("x-csrf-token"), "synthetic-csrf");
    assert.equal(headers.get("cookie"), "__Host-lv_session=synthetic-session");
    assert.equal(headers.get("sec-fetch-site"), "same-origin");
    assert.equal(headers.get("sec-fetch-mode"), "cors");
    return Response.json({}, { headers: { "Set-Cookie": "__Host-lv_session=; Max-Age=0; Path=/; Secure; HttpOnly; SameSite=Lax" } });
  });
  assert.equal(calls, 1); assert.equal(response.status, 200);
  assert.match(response.headers.get("set-cookie")!, /Max-Age=0; Path=\/; Secure; HttpOnly; SameSite=Lax/);
});

test("production proxy keeps Origin and CSRF checks even over private HTTP", async () => {
  const invalid: Record<string, string>[] = [
    { Origin: "https://evil.example", "X-CSRF-Token": "synthetic" },
    { Origin: config.webOrigin, "X-CSRF-Token": "" },
    { Origin: "", "X-CSRF-Token": "synthetic" },
    { Origin: config.webOrigin, "X-CSRF-Token": "synthetic", "Sec-Fetch-Site": "cross-site" },
  ];
  for (const headers of invalid) {
    const request = new Request(config.webOrigin + "/api/auth/otp/request", { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: "{}" });
    assert.equal((await forward(request, config, async () => { throw new Error("must not call"); })).status, 403);
  }
});

test("server-side public reads generate HTTPS forwarding without identity", async () => {
  const api = publicApi(config, async (_url, init) => {
    const headers = new Headers(init?.headers);
    assert.equal(headers.get("x-forwarded-proto"), "https");
    for (const name of ["cookie", "authorization", "origin", "referer", "x-csrf-token", "x-forwarded-for", "x-forwarded-host"]) assert.equal(headers.get(name), null);
    assert.equal(init?.redirect, "manual");
    return Response.json({ items: [], total: 0, page: 1, limit: 20 });
  });
  await api.properties();
  assert.deepEqual([...backendHeaders(config).keys()].sort(), ["accept", "x-forwarded-proto"]);
});

test("health validates runtime configuration and readiness hides dependency details", async () => {
  const noNetwork: typeof fetch = async () => { throw new Error("liveness must not access dependencies"); };
  assert.equal((await health(environment, false, noNetwork)).status, 200);
  assert.equal((await health({ NODE_ENV: "production" }, false, noNetwork)).status, 503);
  const ready = await health(environment, true, async (url, init) => {
    assert.equal(url, "http://api:8000/ready");
    assert.equal(new Headers(init?.headers).get("x-forwarded-proto"), "https");
    assert.equal(init?.credentials, "omit"); assert.equal(init?.redirect, "error");
    return Response.json({ private: "dependency-details" }, { headers: { "Set-Cookie": "do-not-forward=synthetic" } });
  });
  assert.equal(ready.status, 200); assert.deepEqual(await ready.json(), { status: "ok" });
  assert.equal(ready.headers.get("set-cookie"), null); assert.equal(ready.headers.get("cache-control"), "no-store");
  for (const transport of [async () => Response.json({ private: "details" }, { status: 503 }), async () => { throw new Error("private-diagnostic"); }]) {
    const response = await health(environment, true, transport);
    assert.equal(response.status, 503); assert.deepEqual(await response.json(), { status: "unavailable" });
  }
});

test("all server backend callers apply generated transport headers", async () => {
  for (const path of ["lib/server-api.ts", "lib/admin-server.ts", "lib/published-content.ts", "app/(public)/legal/[doc]/page.tsx"]) {
    const source = await readFile(new URL("../src/" + path, import.meta.url), "utf8");
    assert.match(source, /backendHeaders\(config\)/, path);
    assert.match(source, /redirect: "error"/, path);
  }
});

test("Docker uses standalone Node 24, non-root listener, secret exclusions and liveness", async () => {
  const docker = await readFile(new URL("../Dockerfile", import.meta.url), "utf8");
  assert.match(docker, /FROM gcr.io\/distroless\/nodejs24-debian13:nonroot@sha256:[a-f0-9]{64} AS runtime/);
  assert.match(docker, /HOSTNAME=0\.0\.0\.0 PORT=3000/);
  assert.match(docker, /USER 1000:1000/); assert.match(docker, /\/app\/\.next\/standalone/);
  assert.match(docker, /\/app\/\.next\/static/); assert.match(docker, /\/app\/public/);
  assert.match(docker, /HEALTHCHECK.*\/health/); assert.match(docker, /CMD \["node", "server\.js"\]/);
  const ignored = await readFile(new URL("../.dockerignore", import.meta.url), "utf8");
  assert.match(ignored, /^\.env\*$/m); assert.match(ignored, /^node_modules$/m); assert.match(ignored, /^\.next$/m);
  const next = await readFile(new URL("../next.config.ts", import.meta.url), "utf8");
  assert.match(next, /output: "standalone"/);
});
