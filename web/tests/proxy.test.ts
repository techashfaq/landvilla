import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { once } from "node:events";
import { forward, sessionCookie } from "../src/lib/proxy.ts";
const config = { backendOrigin: "http://127.0.0.1:8000", webOrigin: "http://localhost:19006", production: false };
const post = (headers: Record<string, string> = {}) => new Request(config.webOrigin + "/api/auth/otp/request", { method: "POST", headers: { Origin: config.webOrigin, "Content-Type": "application/json", "X-CSRF-Token": "fixture-csrf", ...headers }, body: JSON.stringify({ identifier: "test@example.test", purpose: "login" }) });

test("proxy denies unavailable mutations, bearer credentials, query tokens and malicious paths", async () => {
  let calls = 0;
  const transport: typeof fetch = async () => { calls++; return Response.json({}); };
  for (const request of [
    new Request(config.webOrigin + "/api/admin/listings/x/approve", { method: "POST" }),
    new Request(config.webOrigin + "/api/auth/me?token=fixture"),
    new Request(config.webOrigin + "/api/auth/me", { headers: { Authorization: "Bearer fixture" } }),
    new Request(config.webOrigin + "/api/%2e%2e/auth/me"),
    new Request(config.webOrigin + "/api/auth/session", { method: "POST" }),
  ]) assert.ok((await forward(request, config, transport)).status >= 400);
  assert.equal(calls, 0);
});
test("proxy requires trusted Origin and CSRF before forwarding unsafe requests", async () => {
  const transport: typeof fetch = async () => { throw new Error("must not forward"); };
  for (const request of [post({ Origin: "https://evil.example" }), post({ "X-CSRF-Token": "" }), post({ "Sec-Fetch-Site": "cross-site" }), post({ Origin: "null" })]) assert.equal((await forward(request, config, transport)).status, 403);
  const missing = post(); missing.headers.delete("Origin");
  assert.equal((await forward(missing, config, transport)).status, 403);
});
test("proxy preserves JSON body, cookie/CSRF/Origin and discards untrusted forwarding headers", async () => {
  const request = post({ Cookie: "tracking=fixture; lv_dev_session=fixture-cookie", "X-Forwarded-For": "fixture-address", "X-Forwarded-Host": "evil.example" });
  const transport: typeof fetch = async (input, init) => {
    assert.equal(input, config.backendOrigin + "/api/auth/otp/request");
    const headers = new Headers(init?.headers);
    assert.equal(headers.get("Cookie"), "lv_dev_session=fixture-cookie");
    assert.equal(headers.get("Origin"), config.webOrigin);
    assert.equal(headers.get("X-CSRF-Token"), "fixture-csrf");
    assert.equal(headers.get("X-LV-Client"), "web");
    assert.equal(headers.get("X-Forwarded-For"), null);
    assert.equal(headers.get("Authorization"), null);
    assert.equal(init?.redirect, "manual");
    assert.equal(init?.cache, "no-store");
    assert.equal(JSON.parse(String(init?.body)).purpose, "login");
    return Response.json({ ok: true });
  };
  assert.equal((await forward(request, config, transport)).status, 200);
});
test("proxy preserves individual HttpOnly cookies and logout deletion attributes", async () => {
  const headers = new Headers({ "Content-Type": "application/json" });
  headers.append("Set-Cookie", "lv_dev_session=fixture; Path=/; HttpOnly; SameSite=Lax");
  headers.append("Set-Cookie", "lv_dev_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax");
  const response = await forward(new Request(config.webOrigin + "/api/auth/browser/bootstrap"), config, async () => new Response("{}", { headers }));
  assert.equal(response.headers.getSetCookie().length, 2);
  assert.match(response.headers.getSetCookie()[0]!, /HttpOnly; SameSite=Lax/);
  assert.match(response.headers.getSetCookie()[1]!, /Max-Age=0/);
  assert.equal(response.headers.get("Cache-Control"), "no-store");
});
test("HTTPS proxy fails closed on insecure, domain-scoped or wrong-name backend cookies", async () => {
  const secure = { backendOrigin: "https://api.example.test", webOrigin: "https://example.test", production: true };
  for (const cookie of ["lv_dev_session=fixture; Path=/; HttpOnly; SameSite=Lax", "__Host-lv_session=fixture; Path=/; HttpOnly; SameSite=Lax", "__Host-lv_session=fixture; Path=/; Secure; HttpOnly; SameSite=Lax; Domain=example.test"]) {
    const response = await forward(new Request(secure.webOrigin + "/api/auth/browser/bootstrap"), secure, async () => Response.json({}, { headers: { "Set-Cookie": cookie } }));
    assert.equal(response.status, 502); assert.equal(response.headers.getSetCookie().length, 0);
  }
  const response = await forward(new Request(secure.webOrigin + "/api/auth/browser/bootstrap"), secure, async () => Response.json({}, { headers: { "Set-Cookie": "__Host-lv_session=fixture; Path=/; Secure; HttpOnly; SameSite=Lax" } }));
  assert.equal(response.status, 200);
});
test("cookie extraction accepts only the appropriate single host cookie", () => {
  assert.equal(sessionCookie("other=fixture; __Host-lv_session=secure; lv_dev_session=local", true), "__Host-lv_session=secure");
  assert.equal(sessionCookie("lv_dev_session=a; lv_dev_session=b", false), null);
  assert.equal(sessionCookie("other=fixture", false), null);
});
test("proxy bounds body size, requires JSON and rejects redirects/HTML without leaking content", async () => {
  assert.equal((await forward(post({ "Content-Length": "40000" }), config)).status, 413);
  assert.equal((await forward(post({ "Content-Type": "text/plain" }), config)).status, 415);
  const large = new Request(config.webOrigin + "/api/auth/google", { method: "POST", headers: { Origin: config.webOrigin, "X-CSRF-Token": "fixture", "Content-Type": "application/json" }, body: JSON.stringify({ id_token: "x".repeat(40000) }) });
  assert.equal((await forward(large, config)).status, 413);
  for (const upstream of [new Response("private-stack", { status: 500 }), new Response(null, { status: 302, headers: { Location: "https://evil.example" } })]) {
    const response = await forward(new Request(config.webOrigin + "/api/meta"), config, async () => upstream);
    assert.equal(response.status, 502); assert.ok(!(await response.text()).includes("private-stack"));
  }
});
test("network outage and backend internal errors are sanitized; throttling retained", async () => {
  const request = () => new Request(config.webOrigin + "/api/meta");
  const unavailable = await forward(request(), config, async () => { throw new Error("private-uri"); });
  assert.equal(unavailable.status, 503); assert.ok(!(await unavailable.text()).includes("private-uri"));
  const error = await forward(request(), config, async () => Response.json({ detail: "private-stack" }, { status: 500 }));
  assert.equal(error.status, 503); assert.ok(!(await error.text()).includes("private-stack"));
  const limited = await forward(post(), config, async () => Response.json({ detail: "Wait" }, { status: 429, headers: { "Retry-After": "60" } }));
  assert.equal(limited.status, 429); assert.equal(limited.headers.get("retry-after"), "60");
});
test("integration: real loopback HTTP upstream receives browser-only contract", async () => {
  const received: { method?: string; path?: string; body?: string; authorization?: string; csrf?: string } = {};
  const server = http.createServer(async (request, response) => {
    const chunks: Buffer[] = []; for await (const chunk of request) chunks.push(Buffer.from(chunk));
    received.method = request.method; received.path = request.url; received.body = Buffer.concat(chunks).toString();
    received.authorization = request.headers.authorization; received.csrf = String(request.headers["x-csrf-token"]);
    response.writeHead(200, { "Content-Type": "application/json", "Set-Cookie": ["lv_dev_session=fixture; HttpOnly; Path=/; SameSite=Lax"] });
    response.end(JSON.stringify({ user: null, csrf_token: "fixture", expires_in: 900 }));
  });
  server.listen(0, "127.0.0.1"); await once(server, "listening");
  try {
    const address = server.address(); assert.ok(address && typeof address !== "string");
    const response = await forward(post(), { ...config, backendOrigin: `http://127.0.0.1:${address.port}` });
    assert.equal(response.status, 200); assert.equal(received.method, "POST");
    assert.equal(received.path, "/api/auth/otp/request"); assert.equal(received.csrf, "fixture-csrf"); assert.equal(received.authorization, undefined);
    assert.equal(JSON.parse(received.body!).identifier, "test@example.test"); assert.equal(response.headers.getSetCookie().length, 1);
  } finally { server.closeAllConnections(); await new Promise<void>(resolve => server.close(() => resolve())); }
});
