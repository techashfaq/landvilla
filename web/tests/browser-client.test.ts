import test from "node:test";
import assert from "node:assert/strict";
import { BrowserClient } from "../src/lib/browser-client.ts";
const account = { user_id: "fixture-user", name: "Test Buyer", email: "test@example.test", role: "buyer" };
const session = (signedIn = false) => ({ user: signedIn ? account : null, csrf_token: "fixture-csrf", expires_in: 900 });
const challenge = { challenge_id: "fixture-challenge-00000", expires_in: 300, resend_after: 60 };

test("OTP flow bootstraps cookie session and sends CSRF without bearer", async () => {
  const paths: string[] = [];
  const client = new BrowserClient(async (input, init) => {
    paths.push(String(input)); const headers = new Headers(init?.headers);
    assert.equal(init?.credentials, "same-origin"); assert.equal(headers.get("Authorization"), null);
    if (String(input).endsWith("bootstrap")) return Response.json(session());
    assert.equal(headers.get("X-CSRF-Token"), "fixture-csrf");
    if (String(input).endsWith("request")) return Response.json(challenge);
    return Response.json(session(true));
  });
  const result = await client.requestOtp({ identifier: "test@example.test", purpose: "login" });
  assert.equal(result.resend_after, 60);
  await client.verifyOtp(result.challenge_id, "123456");
  assert.equal(client.snapshot().session?.user?.role, "buyer"); assert.equal(paths.length, 3);
});
test("malformed/native session response never signs browser in", async () => {
  const client = new BrowserClient(async input => Response.json(String(input).endsWith("bootstrap") ? session() : { ...session(true), session_token: "fixture-native" }));
  await assert.rejects(client.google("fixture-google-token")); assert.equal(client.snapshot().session?.user, null);
});
test("missing Google credential sends no request; backend rejection never signs in", async () => {
  let count = 0;
  const client = new BrowserClient(async input => { count++; return String(input).endsWith("bootstrap") ? Response.json(session()) : Response.json({ detail: "private-provider-error" }, { status: 401 }); });
  await assert.rejects(client.google("")); assert.equal(count, 0);
  await assert.rejects(client.google("fixture-google"), error => error instanceof Error && !error.message.includes("private-provider-error"));
  assert.equal(client.snapshot().session, null);
});
test("nonce and Google ID token use existing endpoints; only backend cookie result accepted", async () => {
  let nonceCalled = false; let tokenCalled = false;
  const client = new BrowserClient(async (input, init) => {
    if (String(input).endsWith("bootstrap")) return Response.json(session());
    if (String(input).endsWith("google-nonce")) { nonceCalled = true; return Response.json({ nonce: "fixture-nonce" }); }
    tokenCalled = true; assert.deepEqual(JSON.parse(String(init?.body)), { id_token: "fixture-google" });
    return Response.json(session(true));
  });
  assert.equal(await client.googleNonce(), "fixture-nonce"); await client.google("fixture-google");
  assert.ok(nonceCalled && tokenCalled); assert.equal(client.snapshot().session?.user?.user_id, "fixture-user");
});
test("duplicate taps rejected while one authentication request is pending", async () => {
  let release!: () => void;
  const wait = new Promise<void>(resolve => { release = resolve; });
  const client = new BrowserClient(async input => { if (String(input).endsWith("bootstrap")) return Response.json(session()); await wait; return Response.json(challenge); });
  await client.bootstrap(); const first = client.requestOtp({ identifier: "test@example.test", purpose: "login" });
  await assert.rejects(client.requestOtp({ identifier: "test@example.test", purpose: "login" }), /in progress/);
  release(); await first;
});
test("late success cannot restore a session invalidated by another tab", async () => {
  let release!: () => void; const wait = new Promise<void>(resolve => { release = resolve; });
  const client = new BrowserClient(async input => { if (String(input).endsWith("bootstrap")) return Response.json(session()); await wait; return Response.json(session(true)); });
  await client.bootstrap(); const attempt = client.google("fixture-google"); client.invalidate(); release();
  await assert.rejects(attempt); assert.equal(client.snapshot().session, null);
});
test("network failures preserve session and permit a later attempt", async () => {
  let fail = true;
  const client = new BrowserClient(async input => { if (String(input).endsWith("bootstrap")) return Response.json(session()); if (fail) throw new Error("fixture-private-network"); return Response.json(challenge); });
  await client.bootstrap(); await assert.rejects(client.requestOtp({ identifier: "test@example.test", purpose: "login" }), /Unable to connect/);
  assert.ok(client.snapshot().session); fail = false;
  assert.equal((await client.requestOtp({ identifier: "test@example.test", purpose: "login" })).resend_after, 60);
});
test("logout revokes via CSRF and clears local identity; failure reports unconfirmed revocation", async () => {
  for (const fail of [false, true]) {
    const client = new BrowserClient(async input => String(input).endsWith("bootstrap") ? Response.json(session(true)) : Response.json({}, { status: fail ? 503 : 200 }));
    await client.bootstrap();
    if (fail) await assert.rejects(client.logout()); else await client.logout();
    assert.equal(client.snapshot().session, null);
    if (fail) assert.match(client.snapshot().error, /could not be confirmed/);
  }
});
test("expired/revoked session with non-JSON error still clears private identity", async () => {
  const client = new BrowserClient(async input => String(input).endsWith("bootstrap") ? Response.json(session(true)) : new Response("fixture-private-html", { status: 401 }));
  await client.bootstrap(); await assert.rejects(client.googleNonce());
  assert.equal(client.snapshot().session, null); assert.match(client.snapshot().error, /expired or was revoked/);
});
test("bootstrap deduplicates requests and explicit invalidation clears state", async () => {
  let count = 0; const client = new BrowserClient(async () => { count++; return Response.json(session(true)); });
  await Promise.all([client.bootstrap(), client.bootstrap()]); assert.equal(count, 1);
  client.invalidate(); assert.equal(client.snapshot().session, null);
});
