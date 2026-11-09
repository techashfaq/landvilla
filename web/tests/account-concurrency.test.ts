import test from 'node:test';
import assert from 'node:assert/strict';
import { BrowserClient, ApiError } from '../src/lib/browser-client.ts';
function deferred<T>() { let resolve!: (v:T)=>void; let reject!: (e:Error)=>void; const promise=new Promise<T>((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject}; }
const session=(id='a')=>({user:{user_id:id,name:'Fixture',email:'fixture@example.test',role:'buyer'},csrf_token:'fixture-'+id,expires_in:900});
function setup() {
  const reads: ReturnType<typeof deferred<Response>>[]=[]; const writes: ReturnType<typeof deferred<Response>>[]=[];
  let identity='a';
  const client=new BrowserClient(async (path,init)=>{
    if(String(path).endsWith('bootstrap'))return Response.json(session(identity));
    assert.equal(new Headers(init?.headers).has('Authorization'),false);
    assert.equal(init?.credentials,'same-origin');
    assert.ok(new Headers(init?.headers).get('X-CSRF-Token'));
    if(String(path).endsWith('logout'))return Response.json({ok:true});
    if(String(path).endsWith('google'))return Response.json(session('b'));
    const request=deferred<Response>();(init?.method==='GET'?reads:writes).push(request);return request.promise;
  });return {client,reads,writes,replace:()=>{identity='b';}};
}
test('S15 simultaneous safe account reads succeed independently',async()=>{const {client,reads}=setup();await client.bootstrap();const a=client.account('/api/saved'),b=client.account('/api/enquiries/me');assert.equal(reads.length,2);reads[1]!.resolve(Response.json({id:'second'}));reads[0]!.resolve(Response.json({id:'first'}));assert.deepEqual(await Promise.all([a,b]),[{id:'first'},{id:'second'}]);});
test('S15 mutations remain exclusive while reads can proceed',async()=>{const {client,reads,writes}=setup();await client.bootstrap();const a=client.account('/api/saved/fixture','POST',{});await assert.rejects(client.account('/api/saved/other','DELETE',{}),/in progress/);const read=client.account('/api/saved');reads[0]!.resolve(Response.json({items:[]}));await read;writes[0]!.resolve(Response.json({saved:true}));await a;assert.equal(writes.length,1);});
for(const mode of ['logout','google','bootstrap','invalidate'] as const)test('S15 stale read rejected after '+mode,async()=>{const s=setup();await s.client.bootstrap();const read=s.client.account('/api/saved');const rejected=assert.rejects(read,(e:unknown)=>e instanceof ApiError && e.status===409);if(mode==='logout')await s.client.logout();if(mode==='google')await s.client.google('synthetic');if(mode==='bootstrap'){s.replace();await s.client.bootstrap();}if(mode==='invalidate')s.client.invalidate();s.reads[0]!.resolve(Response.json({private:'old identity fixture'}));await rejected;assert.equal(s.client.snapshot().session?.user?.user_id,mode==='google'||mode==='bootstrap'?'b':undefined);});
test('S15 errors are sanitized and another read remains usable',async()=>{const s=setup();await s.client.bootstrap();const a=s.client.account('/api/saved');s.reads[0]!.resolve(Response.json({detail:'sensitive-fixture'},{status:403}));await assert.rejects(a,(e:unknown)=>e instanceof Error&&!e.message.includes('sensitive-fixture'));const b=s.client.account('/api/saved');s.reads[1]!.resolve(Response.json({items:[]}));await b;});
test('S15 identity change during body decoding rejects late success',async()=>{const gate=deferred<unknown>();const s=setup();await s.client.bootstrap();const a=s.client.account('/api/saved');const denied=assert.rejects(a);const response=Response.json({});response.json=()=>gate.promise;s.reads[0]!.resolve(response);await new Promise(r=>setImmediate(r));s.client.invalidate();gate.resolve({items:[]});await denied;});
