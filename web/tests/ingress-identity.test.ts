import test from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { ingressIdentity } from "../src/lib/ingress-identity.ts";
import { forward } from "../src/lib/proxy.ts";
const env = { CLIENT_IP_MODE: "signed-v1", LANDVILLA_INGRESS_TOKEN: "d".repeat(64), WEB_API_IP_KEY: "e".repeat(64) };
const config = { production:true, webOrigin:"https://landvilla.in", backendOrigin:"http://api:8000" };
const request = (headers:Record<string,string>={}) => new Request(config.webOrigin+"/api/auth/browser/bootstrap", {headers:{"X-LV-Ingress-Token":env.LANDVILLA_INGRESS_TOKEN,"X-LV-Client-IP":"203.0.113.10",...headers}});
test("ingress rejects missing, duplicate, malformed or unauthenticated client identity",()=>{
 for(const headers of [{"X-LV-Ingress-Token":""},{"X-LV-Ingress-Token":"a".repeat(64)},{"X-LV-Client-IP":"1.2.3.4,5.6.7.8"},{"X-LV-Client-IP":"fe80::1%eth0"}] as Record<string,string>[]) assert.throws(()=>ingressIdentity(request(headers),env));
 assert.throws(()=>ingressIdentity(request(),{...env,WEB_API_IP_KEY:env.LANDVILLA_INGRESS_TOKEN}));
});
test("ingress signs method path timestamp and direct client address",()=>{
 const headers=ingressIdentity(request(),env,1800000000000);
 assert.equal(headers.get("x-lv-ip-signature"),createHmac("sha256",Buffer.from(env.WEB_API_IP_KEY,"hex")).update("v1\n1800000000\nGET\n/api/auth/browser/bootstrap\n203.0.113.10").digest("hex"));
});
test("browser forwarding claims and ingress token never reach API",async()=>{
 const input=request({"X-Forwarded-For":"1.2.3.4","X-LV-IP-Signature":"attacker","Origin":config.webOrigin});
 const trusted=ingressIdentity(input,env);
 const response=await forward(input,config,async(_url,init)=>{
   const headers=new Headers(init?.headers);
   assert.equal(headers.get("x-forwarded-for"),null); assert.equal(headers.get("x-lv-ingress-token"),null);
   assert.equal(headers.get("x-lv-ip-signature"),trusted.get("x-lv-ip-signature"));
   return Response.json({});
 },trusted);
 assert.equal(response.status,200);
});
