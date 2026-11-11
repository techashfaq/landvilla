const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
function load(file, require) {
  const ctx = { exports: {}, require };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText, ctx);
  return ctx.exports;
}
test('focused refresh runs on focus and foreground and removes its listener on blur', () => {
  let focus, listener, removed = 0, refreshed = 0;
  const hook = load('src/useFocusedRefresh.ts', name => name === 'expo-router' ? { useFocusEffect: cb => { focus = cb; } } : name === 'react' ? { useCallback: cb => cb } : { AppState: { addEventListener: (event, cb) => { assert.equal(event, 'change'); listener = cb; return { remove: () => removed++ }; } } });
  hook.useFocusedRefresh(async () => { refreshed++; }, true);
  const cleanup = focus(); assert.equal(refreshed, 1);
  listener('background'); assert.equal(refreshed, 1);
  listener('active'); assert.equal(refreshed, 2);
  cleanup(); assert.equal(removed, 1);
});
test('signed-out screens never refresh private data', () => {
  let focus;
  const hook = load('src/useFocusedRefresh.ts', name => name === 'expo-router' ? { useFocusEffect: cb => { focus = cb; } } : name === 'react' ? { useCallback: cb => cb } : { AppState: { addEventListener: () => assert.fail('unexpected listener') } });
  hook.useFocusedRefresh(async () => assert.fail('unexpected request'), false);
  assert.equal(focus(), undefined);
});
function dashboard(status, error = false) {
  const jsx = (type, props) => ({ type, props });
  const navigated = [];
  const mod = load('app/broker/index.tsx', name => {
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx };
    if (name === 'expo-router') return { useRouter: () => ({ push: x => navigated.push(x) }) };
    if (name === 'react-native') return { View: 'View', Text: 'Text', ScrollView: 'ScrollView' };
    if (name === 'react-native-safe-area-context') return { useSafeAreaInsets: () => ({ top: 0, bottom: 0 }) };
    if (name === '@/src/auth') return { useAuth: () => ({ user: { user_id: 'broker' }, loading: false }) };
    if (name === '@/src/lister') return { useBrokerDashboard: () => ({ data: { application: status ? { status, full_name: 'Test' } : null, listings: { active: 2, pending_review: 1 }, leads: { new: 4 } }, isError: error, error: new Error('offline'), refetch: async () => {} }) };
    if (name === '@/src/useFocusedRefresh') return { useFocusedRefresh: () => {} };
    if (name === '@/src/theme') return { makeStyles: () => () => ({}) };
    if (name === '@/src/components/ui') return { Button: 'Button', Badge: 'Badge', EmptyState: 'EmptyState' };
    return {};
  });
  const nodes = [];
  function walk(node) { if (!node || typeof node !== 'object') return; nodes.push(node); for (const c of [node.props?.children].flat(Infinity)) walk(c); }
  walk(mod.default()); return { nodes, navigated };
}
test('only approved brokers see the broker listing action', () => {
  for (const status of [null, 'pending', 'rejected', 'suspended', 'approved']) {
    const h = dashboard(status);
    const create = h.nodes.find(n => n.props?.label === 'Create broker listing');
    assert.equal(!!create, status === 'approved');
    if (create) { create.props.onPress(); assert.deepEqual(h.navigated, ['/post/form?as=broker']); }
    assert.equal(h.nodes.some(n => n.props?.label === 'Revise and resubmit'), status === 'rejected');
  }
});
test('dashboard request failure is retryable and does not display fabricated zero metrics', () => {
  const h = dashboard('approved', true);
  assert.ok(h.nodes.find(n => n.type === 'EmptyState' && n.props.cta === 'Retry'));
  assert.equal(h.nodes.some(n => n.props?.label === 'Create broker listing'), false);
});
function applicationHarness() {
  let slots = [], cursor = 0, mutation, submitted, finishUpload, uploads = 0;
  const jsx = (type, props) => ({ type, props });
  const react = { useEffect: () => {}, useRef: value => { const i = cursor++; return slots[i] ??= { current: value }; }, useState: value => { const i = cursor++; if (!(i in slots)) slots[i] = value; return [slots[i], value => { slots[i] = typeof value === 'function' ? value(slots[i]) : value; }]; } };
  const mod = load('app/broker/apply.tsx', name => {
    if (name === 'react') return react;
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx };
    if (name === '@tanstack/react-query') return { useQueryClient: () => ({ invalidateQueries: () => {} }), useMutation: options => { mutation = options; return { mutate: () => { submitted = options.mutationFn(); }, isPending: false }; } };
    if (name === 'expo-router') return { useRouter: () => ({}) };
    if (name === 'expo-document-picker') return { getDocumentAsync: async () => ({ canceled: false, assets: [{ uri: 'file:///proof.pdf', name: 'proof.pdf', size: 100 }] }) };
    if (name === 'react-native') return { View: 'View', Text: 'Text', TextInput: 'Input', Pressable: 'Pressable' };
    if (name === 'react-native-safe-area-context') return { useSafeAreaInsets: () => ({ top: 0, bottom: 0 }) };
    if (name === '@/src/auth') return { useAuth: () => ({ user: { user_id: 'owner' } }) };
    if (name === '@/src/lister') return { useBrokerDashboard: () => ({ data: { application: null }, refetch: async () => {} }) };
    if (name === '@/src/data') return { useMeta: () => ({ data: { localities: [{ id: 'ujjain-locality', name_en: 'Test locality' }] } }) };
    if (name === '@/src/useFocusedRefresh') return { useFocusedRefresh: () => {} };
    if (name === '@/src/theme') return { makeStyles: () => () => ({}), useTheme: () => ({ colors: {} }) };
    if (name === '@/src/i18n') return { useLang: () => ({ tx: x => x }) };
    if (name === '@/src/components/Toast') return { useToast: () => ({ show: () => {} }) };
    if (name === '@/src/components/PhotoPicker') return { uploadFile: async (_asset, kind) => { assert.equal(kind, 'broker_doc'); uploads++; return new Promise(resolve => { finishUpload = () => resolve({ id: 'private-proof' }); }); } };
    if (name === '@/src/api') return { api: async (_path, options) => options.body };
    if (name === '@/src/components/ui') return { Button: 'Button', Chip: 'Chip', Checkbox: 'Checkbox' };
    return {};
  });
  function render() { cursor = 0; const nodes = []; function walk(node) { if (!node || typeof node !== 'object') return; nodes.push(node); for (const c of [node.props?.children].flat(Infinity)) walk(c); } walk(mod.default().type()); return nodes; }
  const find = id => render().find(n => n.props?.testID === id);
  return { render, find, get submitted() { return submitted; }, get mutation() { return mutation; }, get uploads() { return uploads; }, finish: () => finishUpload() };
}
test('broker form validates locality and locks submission until private document upload finishes', async () => {
  const h = applicationHarness();
  h.find('broker-name-input').props.onChangeText('Test Broker');
  h.find('broker-phone-input').props.onChangeText('9876543210');
  h.find('broker-submit-btn').props.onPress();
  assert.match(h.find('broker-form-error').props.children, /locality/);
  h.render().find(n => n.type === 'Chip').props.onPress();
  h.find('broker-declaration-checkbox').props.onToggle();
  const upload = h.find('broker-add-doc-btn').props.onPress();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.find('broker-submit-btn').props.disabled, true);
  h.find('broker-submit-btn').props.onPress();
  assert.equal(h.submitted, undefined);
  h.finish(); await upload;
  assert.equal(h.uploads, 1);
  assert.ok(h.find('broker-doc-remove-private-proof'));
  assert.equal(h.find('broker-submit-btn').props.disabled, false);
});
