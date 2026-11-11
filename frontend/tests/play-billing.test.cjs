const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const source = ts.transpileModule(fs.readFileSync('src/components/PlayBillingPanel.tsx', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
async function harness(status) {
  let receive, effect, finished = 0, version = 1, restored = 0, cleanup;
  const sdk = { initConnection: async () => true, endConnection: async () => {}, purchaseUpdatedListener: cb => { receive = cb; return { remove() {} }; }, purchaseErrorListener: () => ({ remove() {} }), getAvailablePurchases: async () => { restored++; return []; }, fetchProducts: async () => [{ id: 'featured.test', displayPrice: '₹99.00' }], finishTransaction: async () => { finished++; }, ErrorCode: { UserCancelled: 'cancelled' } };
  const ctx = { exports: {}, require: name => {
    if (name === 'react') return { useEffect: cb => { effect = cb; }, useRef: v => ({ current: v }), useState: v => [v, () => {}] };
    if (name === 'react/jsx-runtime') return { jsx: () => null, jsxs: () => null };
    if (name === 'react-native') return { Platform: { OS: 'android' }, AppState: { addEventListener: () => ({ remove() {} }) } };
    if (name === 'expo-constants') return { default: { appOwnership: 'standalone' } };
    if (name === 'expo-crypto') return { randomUUID: () => 'synthetic-uuid-000001' };
    if (name === '@/src/auth') return { useAuth: () => ({ user: { user_id: 'owner' } }) };
    if (name === '@tanstack/react-query') return { useQueryClient: () => ({ invalidateQueries: async () => {} }) };
    if (name === '@/src/api') return { getApiSessionVersion: () => version, api: async () => { if (status === 'error') throw new Error('offline'); return { status }; } };
    if (name === 'react-native-iap') return sdk;
    return {};
  }};
  vm.runInNewContext(source, ctx);
  ctx.exports.PlayBillingPanel({ productId: 'featured.test', planId: 'plan', propertyId: 'property' });
  cleanup = effect(); await new Promise(resolve => setImmediate(resolve));
  return { receive: async () => { receive({ purchaseToken: 'synthetic-token' }); await new Promise(resolve => setImmediate(resolve)); }, get finished() { return finished; }, get restored() { return restored; }, logout: () => version++, cleanup };
}
test('Play purchase is consumed only after server-confirmed entitlement', async () => {
  const h = await harness('paid'); await h.receive(); assert.equal(h.finished, 1); assert.equal(h.restored, 1); h.cleanup();
});
test('pending, failed and offline verification never consume a Play purchase', async () => {
  for (const status of ['pending', 'failed', 'error']) { const h = await harness(status); await h.receive(); assert.equal(h.finished, 0); h.cleanup(); }
});
test('a previous account cannot consume a purchase after logout', async () => {
  const h = await harness('paid'); h.logout(); await h.receive(); assert.equal(h.finished, 0); h.cleanup();
});
