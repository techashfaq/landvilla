const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");
const source = ts.transpileModule(fs.readFileSync(path.join(__dirname, "../src/api.ts"), "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
function sessionWrites() {
  const context = { exports: {} };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname, "../src/session-writes.ts"), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, context);
  return new context.exports.SessionWrites();
}
test("logout waits for in-flight storage write and removes the old token", async () => {
  const sessions = sessionWrites(); let stored, release;
  const first = sessions.next();
  const pending = sessions.save(first, () => new Promise(resolve => { release = () => { stored = "old"; resolve(); }; }));
  await new Promise(resolve => setImmediate(resolve));
  const second = sessions.next();
  const cleared = sessions.save(second, async () => { stored = null; });
  release(); await Promise.all([pending, cleared]);
  assert.equal(stored, null); assert.equal(sessions.current(first), false);
});
test("superseded session writes are skipped and failed storage does not block logout", async () => {
  const sessions = sessionWrites(); let stored;
  const old = sessions.next(); const current = sessions.next();
  await sessions.save(old, async () => { stored = "wrong-account"; });
  assert.equal(stored, undefined);
  await assert.rejects(sessions.save(current, async () => { throw Error("storage unavailable"); }));
  await sessions.save(sessions.next(), async () => { stored = null; });
  assert.equal(stored, null);
});
function client(fetch, backend = "https://api.example.test/", platform = "android") {
  const context = { exports: {}, require: () => ({ Platform: { OS: platform } }), process: { env: { EXPO_PUBLIC_BACKEND_URL: backend } }, fetch, URL, AbortController, setTimeout, clearTimeout };
  vm.runInNewContext(source, context);
  return context.exports;
}
test("request uses normalized base URL, bearer token, platform and JSON", async () => {
  let request;
  const c = client(async (...args) => { request = args; return new Response('{"ok":true}'); });
  c.setApiToken("test-only");
  assert.equal((await c.api("/saved/id", { method: "POST", body: { value: 1 } })).ok, true);
  assert.equal(request[0], "https://api.example.test/api/saved/id");
  assert.equal(request[1].headers.Authorization, "Bearer test-only");
  assert.equal(request[1].headers["X-LV-Client"], "android");
  assert.equal(request[1].body, '{"value":1}');
});
test("missing configuration fails before network access", async () => {
  const c = client(() => { throw new Error("must not fetch"); }, "");
  await assert.rejects(c.api("/meta"), /not configured/);
});
test("relative uploaded images and absolute remote images resolve correctly", () => {
  const c = client();
  assert.equal(c.fileUrl("/api/files/example"), "https://api.example.test/api/files/example");
  assert.equal(c.fileUrl("https://images.example.test/a.jpg"), "https://images.example.test/a.jpg");
  assert.equal(c.fileUrl("javascript:alert(1)"), "");
  assert.equal(c.fileUrl("//unexpected.test/file"), "");
});
test("JSON 401 invokes session invalidation", async () => {
  let cleared = 0;
  const c = client(async () => new Response('{"detail":"Not authenticated"}', { status: 401 }));
  c.setApiToken("test-only"); c.setUnauthorizedHandler(() => cleared++);
  await assert.rejects(c.api("/auth/me"), e => e.status === 401);
  assert.equal(cleared, 1);
});
test("non-JSON 401 still invalidates session without leaking HTML", async () => {
  let cleared = 0;
  const c = client(async () => new Response("<h1>internal gateway diagnostic</h1>", { status: 401 }));
  c.setApiToken("test-only"); c.setUnauthorizedHandler(() => cleared++);
  await assert.rejects(c.api("/auth/me"), e => e.status === 401 && !e.message.includes("gateway"));
  assert.equal(cleared, 1);
});
test("network failure preserves session", async () => {
  let cleared = false;
  const c = client(async () => { throw new TypeError("Network unavailable"); });
  c.setApiToken("test-only"); c.setUnauthorizedHandler(() => cleared = true);
  await assert.rejects(c.api("/auth/me")); assert.equal(cleared, false);
});
test("validation errors are useful to the form", async () => {
  const c = client(async () => new Response(JSON.stringify({ detail: [{ loc: ["body", "first_name"], msg: "Value error, Required" }] }), { status: 422 }));
  await assert.rejects(c.api("/me/profile"), /First name: Required/);
});
test("filters omit empty fields and encode lists", () => {
  assert.equal(client().qs({ purpose: "buy", page: 2, empty: "", locality: ["a", "b"], bhk: [] }), "?purpose=buy&page=2&locality=a%2Cb");
});
test("late unauthorized response from previous account cannot clear new session", async () => {
  let resolve, cleared = false;
  const c = client(() => new Promise(done => { resolve = done; }));
  c.setApiToken("old-session"); c.setUnauthorizedHandler(() => cleared = true);
  const pending = c.api("/auth/me");
  c.setApiToken("new-session");
  resolve(new Response('{"detail":"Not authenticated"}', { status: 401 }));
  await assert.rejects(pending);
  assert.equal(cleared, false); assert.equal(c.getApiToken(), "new-session");
});

// Exercise the actual AuthProvider with deterministic hook/storage/network adapters.
function authHarness(apiCall, platform = "android", googleToken = async () => null) {
  const slots = []; let cursor = 0; const effects = []; const persisted = new Map();
  const counters = { clear: 0, cancel: 0 }; let unauthorized;
  const react = {
    createContext: () => ({ Provider: "provider" }),
    createElement: (type, props) => ({ type, props }),
    useState: initial => { const i = cursor++; if (!(i in slots)) slots[i] = initial; return [slots[i], value => { slots[i] = typeof value === "function" ? value(slots[i]) : value; }]; },
    useRef: initial => { const i = cursor++; return slots[i] ??= { current: initial }; },
    useCallback: (fn, deps) => { const i = cursor++; if (!slots[i] || deps.some((v, n) => v !== slots[i].deps[n])) slots[i] = { fn, deps }; return slots[i].fn; },
    useEffect: (fn, deps) => { const i = cursor++; if (!slots[i] || deps.some((v, n) => v !== slots[i][n])) { slots[i] = deps; effects.push(fn); } },
  };
  const writes = sessionWrites().constructor;
  let token = null;
  const modules = {
    react, "react-native": { Platform: { OS: platform } },
    "expo-linking": { getInitialURL: async () => null, createURL: () => "landvilla://", addEventListener: () => ({ remove() {} }) },
    "@/src/native-google": { requestNativeGoogleToken: googleToken, nativeGoogleError: () => "Safe sign-in error" },
    "@/src/api": { api: apiCall, setApiToken: value => { token = value; }, setUnauthorizedHandler: fn => { unauthorized = fn; }, setBrowserSession() {}, bootstrapBrowser: async () => ({ user: null, csrf_token: "mock-csrf" }) },
    "@/src/query-client": { queryClient: { cancelQueries: async () => { counters.cancel++; }, clear: () => { counters.clear++; }, invalidateQueries() {} } },
    "@/src/session-writes": { SessionWrites: writes },
    "@/src/utils/storage": { storage: { secureGet: async k => persisted.get(k) ?? null, secureSet: async (k,v) => { persisted.set(k,v); return true; }, secureRemove: async k => { persisted.delete(k); return true; } } },
  };
  const context = { exports: {}, require: name => modules[name], URL,
    window: { addEventListener() {}, removeEventListener() {}, history: { replaceState() {} }, location: { href: "https://landvilla.test/", origin: "https://landvilla.test" }, localStorage: {
      setItem: (k,v) => persisted.set(k,v), getItem: k => persisted.get(k) ?? null, removeItem: k => persisted.delete(k),
    } },
  };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname, "../src/auth.tsx"), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.React, esModuleInterop: true },
  }).outputText, context);
  return {
    render() { cursor = 0; return context.exports.AuthProvider({ children: null }).props.value; },
    async mount() { this.render(); effects.splice(0).forEach(fn => fn()); await new Promise(resolve => setImmediate(resolve)); },
    counters, persisted, token: () => token, expire: () => unauthorized(),
  };
}
const unitSession = id => ({ session_token: "unit-" + id, user: { user_id: id, email: id + "@example.test", role: "buyer" } });
test("AuthProvider ignores late profile responses after switching accounts", async () => {
  let finish;
  const h = authHarness(() => new Promise(resolve => { finish = resolve; }));
  await h.mount(); await h.render().acceptSession(unitSession("first"));
  const refresh = h.render().refreshUser();
  await h.render().acceptSession(unitSession("second"));
  finish(unitSession("first").user); await refresh;
  assert.equal(h.render().user.user_id, "second"); assert.equal(h.token(), "unit-second");
  assert.equal(h.counters.clear, 2);
});
test("late logout cannot clear a newer signed-in account", async () => {
  let finish;
  const h = authHarness(() => new Promise(resolve => { finish = resolve; }));
  await h.mount(); await h.render().acceptSession(unitSession("first"));
  const logout = h.render().logout();
  await h.render().acceptSession(unitSession("second"));
  finish({ ok: true }); await logout;
  assert.equal(h.render().user.user_id, "second"); assert.equal(h.persisted.get("auth_token"), "unit-second");
});
test("revoked session clears profile, persisted token and private queries with a message", async () => {
  const h = authHarness(async () => ({})); await h.mount();
  await h.render().acceptSession(unitSession("first")); h.expire();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.render().user, null); assert.equal(h.token(), null);
  assert.equal(h.persisted.size, 0); assert.match(h.render().error, /expired or was revoked/);
  assert.equal(h.counters.clear, 2);
});
test("native Google cancellation never exchanges a session or signs in", async () => {
  let calls = 0; const h = authHarness(async () => { calls++; }, "android");
  await h.mount(); await h.render().login();
  assert.equal(calls, 0); assert.equal(h.render().user, null);
});

test("OTP form validates registration consent, roles and normalized identifiers", () => {
  const context = { exports: {} };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname, "../src/otp-form.ts"), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText, context);
  const form = context.exports;
  assert.equal(form.normalizeIdentifier(" Owner@Example.Test "), "owner@example.test");
  assert.equal(form.normalizeIdentifier("+91 98765-43210"), "+919876543210");
  for (const invalid of ["", "user@", "1234", "+0123456789"]) assert.equal(form.validIdentifier(invalid), false);
  const args = [" First ", "Last", "owner@example.test", "+91 9876543210", "owner", true, true];
  assert.equal(form.registrationValid(...args), true);
  for (const [i, value] of [[0, " "], [4, "admin"], [5, false], [6, false]]) {
    const bad = [...args]; bad[i] = value; assert.equal(form.registrationValid(...bad), false);
  }
});

test("Google linking errors and provider outages preserve the current session", async () => {
  for (const status of [400, 409, 503]) {
    let cleared = false;
    const c = client(async () => new Response(JSON.stringify({ detail: "Verification unavailable" }), { status }));
    c.setApiToken("current-session"); c.setUnauthorizedHandler(() => { cleared = true; });
    await assert.rejects(c.api("/auth/google/link", { method: "POST", body: { id_token: "test-only" } }), e => e.status === status);
    assert.equal(cleared, false); assert.equal(c.getApiToken(), "current-session");
  }
});
test("profile save errors remain visible without clearing authentication", async () => {
  const c = client(async () => new Response(JSON.stringify({ detail: "Database temporarily unavailable" }), { status: 503 }));
  let cleared = false; c.setApiToken("current-session"); c.setUnauthorizedHandler(() => { cleared = true; });
  await assert.rejects(c.api("/me/profile", { method: "PATCH", body: { first_name: "First", last_name: "Last" } }), /Database temporarily unavailable/);
  assert.equal(cleared, false);
});

test("web API uses cookies and CSRF, never bearer tokens or tokenized file links", async () => {
  const requests = [];
  const c = client(async (url, init) => {
    requests.push({ url, init });
    return new Response(JSON.stringify(url.endsWith("/bootstrap") ? { user: null, csrf_token: "unit-csrf" } : { ok: true }));
  }, "https://api.example.test", "web");
  c.setApiToken("legacy-token");
  await c.api("/me/profile", { method: "PATCH", body: { first_name: "First", last_name: "Last" } });
  assert.equal(requests.length, 2);
  assert.equal(requests[1].init.credentials, "include");
  assert.equal(requests[1].init.headers["X-CSRF-Token"], "unit-csrf");
  assert.equal(requests[1].init.headers.Authorization, undefined);
  assert.equal(c.getApiToken(), null);
  assert.equal(c.fileUrl("/api/files/unit", true), "https://api.example.test/api/files/unit");
  assert.equal((await c.authHeaders())["X-CSRF-Token"], "unit-csrf");
});
test("web AuthProvider removes legacy tokens and accepts only cookie session results", async () => {
  const h = authHarness(async () => ({}), "web");
  h.persisted.set("auth_token", "legacy-token");
  await h.mount();
  assert.equal(h.persisted.has("auth_token"), false);
  await assert.rejects(h.render().acceptSession(unitSession("first")), /cookie session/);
  await h.render().acceptSession({ user: unitSession("first").user, csrf_token: "unit-csrf" });
  assert.equal(h.render().user.user_id, "first");
  assert.equal(h.persisted.has("auth_token"), false);
  assert.equal(h.token(), null);
});
test("web managed sign-in does not exchange or redirect an unbound session", async () => {
  let calls = 0; const h = authHarness(async () => { calls++; }, "web");
  await h.mount(); await h.render().login();
  assert.equal(calls, 0); assert.match(h.render().error, /callback verification/);
});
test("web logout failure reports unconfirmed server revocation", async () => {
  const h = authHarness(async () => { throw Error("offline"); }, "web");
  await h.mount();
  await h.render().acceptSession({ user: unitSession("first").user, csrf_token: "unit-csrf" });
  await h.render().logout();
  assert.equal(h.render().user, null);
  assert.match(h.render().error, /could not be confirmed/);
});
test("late web 401 does not clear a rotated cookie session", async () => {
  let finish; let cleared = false;
  const c = client(() => new Promise(resolve => { finish = resolve; }), "https://api.example.test", "web");
  c.setBrowserSession({ csrf_token: "old-csrf" }); c.setUnauthorizedHandler(() => { cleared = true; });
  const response = c.api("/auth/me");
  c.setBrowserSession({ csrf_token: "new-csrf" });
  finish(new Response('{"detail":"Session expired"}', { status: 401 }));
  await assert.rejects(response); assert.equal(cleared, false);
});

test("failed stale web logout cannot clear a newly accepted account", async () => {
  let fail;
  const h = authHarness(() => new Promise((resolve, reject) => { fail = reject; }), "web");
  await h.mount();
  await h.render().acceptSession({ user: unitSession("first").user, csrf_token: "first-csrf" });
  const logout = h.render().logout();
  await h.render().acceptSession({ user: unitSession("second").user, csrf_token: "second-csrf" });
  fail(Error("offline")); await logout;
  assert.equal(h.render().user.user_id, "second");
  assert.equal(h.render().error, null);
});


test("native Google success exchanges ID token and stores only LANDVILLA session", async () => {
  const calls = [];
  const h = authHarness(async (path, opts) => { calls.push({ path, opts }); return unitSession("google"); }, "android", async () => "google-id-token");
  await h.mount(); await h.render().login();
  assert.equal(calls[0].path, "/auth/google");
  assert.equal(calls[0].opts.body.id_token, "google-id-token");
  assert.equal(h.render().user.user_id, "google");
  assert.equal(h.persisted.get("auth_token"), "unit-google");
  assert.equal(h.token(), "unit-google"); assert.equal(h.render().signingIn, false);
});

test("native Google duplicate taps share one attempt and recover after cancellation", async () => {
  let finish; let count = 0;
  const h = authHarness(async () => unitSession("google"), "android", () => { count++; return new Promise(resolve => { finish = resolve; }); });
  await h.mount(); const pending = h.render().login(); await h.render().login();
  assert.equal(count, 1); assert.equal(h.render().signingIn, true);
  finish(null); await pending;
  assert.equal(h.render().signingIn, false); assert.equal(h.render().user, null);
});

test("native Google backend rejection, network failure and malformed response never establish a session", async () => {
  for (const reply of [async () => { throw { status: 401 }; }, async () => { throw Error("private-token-details"); }, async () => ({ user: unitSession("bad").user })]) {
    const h = authHarness(reply, "android", async () => "google-id-token");
    await h.mount(); await h.render().login();
    assert.equal(h.render().user, null); assert.equal(h.token(), null);
    assert.equal(h.persisted.size, 0); assert.equal(h.render().signingIn, false);
    assert.equal(h.render().error, "Safe sign-in error");
  }
});

test("stale native Google success cannot replace an account accepted during login", async () => {
  let finish;
  const h = authHarness(() => new Promise(resolve => { finish = resolve; }), "android", async () => "google-id-token");
  await h.mount(); const pending = h.render().login(); await new Promise(resolve => setImmediate(resolve));
  await h.render().acceptSession(unitSession("newer")); finish(unitSession("older")); await pending;
  assert.equal(h.render().user.user_id, "newer"); assert.equal(h.token(), "unit-newer");
});

function nativeGoogleHarness(response, overrides = {}) {
  const calls = [];
  const sdk = {
    GoogleOneTapSignIn: { configure: options => calls.push(["configure", options]), checkPlayServices: async () => {}, presentExplicitSignIn: async () => response },
    isCancelledResponse: r => r.type === "cancelled", isSuccessResponse: r => r.type === "success",
  };
  const context = { exports: {}, process: { env: { EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID: "test.apps.googleusercontent.com", ...overrides.env } }, require: name => {
    if (name === "react-native") return { Platform: { OS: "android" } };
    if (name === "expo-constants") return { __esModule: true, default: { appOwnership: overrides.expoGo ? "expo" : null } };
    if (name === "react-native-nitro-google-signin") { if (overrides.missingModule) throw Error("private details"); return sdk; }
    throw Error("Unexpected import");
  } };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname, "../src/native-google.ts"), "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true } }).outputText, context);
  return { ...context.exports, calls };
}

test("native adapter configures Web audience and returns only the ID token", async () => {
  const h = nativeGoogleHarness({ type: "success", data: { idToken: "id-token" } });
  assert.equal(await h.requestNativeGoogleToken(), "id-token");
  assert.equal(h.calls[0][1].offlineAccess, false); assert.equal(h.calls[0][1].autoSelectOnSignIn, false);
});

test("native adapter handles missing token, cancellation, Expo Go and missing build/config safely", async () => {
  assert.equal(await nativeGoogleHarness({ type: "cancelled" }).requestNativeGoogleToken(), null);
  for (const [response, options, pattern] of [
    [{ type: "success", data: {} }, {}, /identity token/],
    [{}, { expoGo: true }, /development build/],
    [{}, { missingModule: true }, /Rebuild/],
    [{}, { env: { EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID: "" } }, /not configured/],
  ]) { await assert.rejects(nativeGoogleHarness(response, options).requestNativeGoogleToken(), pattern); }
  assert.doesNotMatch(nativeGoogleHarness({}).nativeGoogleError(Error("private-token")), /private-token/);
});


test("native session restores from secure storage and authenticates profile refresh", async () => {
  const calls = [];
  const h = authHarness(async path => { calls.push(path); return unitSession("restored").user; });
  h.persisted.set("auth_token", "unit-restored"); await h.mount();
  assert.equal(h.token(), "unit-restored"); assert.equal(h.render().user.user_id, "restored");
  assert.deepEqual(calls, ["/auth/me"]);
});

test("Android plugin permits cleartext only for the development build", () => {
  const code = fs.readFileSync(path.join(__dirname, "../plugins/with-android-google.js"), "utf8");
  for (const profile of ["development", "preview", "production", undefined]) {
    const ctx = { module: { exports: {} }, process: { env: { EAS_BUILD_PROFILE: profile } }, require: () => ({ withAndroidManifest: (config, action) => action(config) }) };
    vm.runInNewContext(code, ctx);
    const config = { modResults: { manifest: { application: [{ $: {} }] } } };
    const result = ctx.module.exports(config);
    assert.equal(result.modResults.manifest.application[0].$["android:usesCleartextTraffic"], profile === "development" ? "true" : "false");
  }
});
