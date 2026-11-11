const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const source = ts.transpileModule(fs.readFileSync('src/components/PhotoPicker.tsx', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
function uploader(uploadForm) {
  let session = 1;
  const ctx = { exports: {}, AbortController, setTimeout, clearTimeout, require: name => {
    if (name === '@/src/api') return { API_BASE: '/api', authHeaders: async () => ({ Authorization: 'test-only' }), getApiSessionVersion: () => session };
    if (name === '@/src/utils/upload') return { uploadForm };
    if (name === '@/src/theme') return { makeStyles: () => () => ({}) };
    return {};
  }};
  vm.runInNewContext(source, ctx);
  return { upload: () => ctx.exports.uploadFile({ uri: 'file:///synthetic.jpg' }, 'property_photo'), changeSession: () => session++ };
}
test('upload uses authenticated multipart and accepts real file response', async () => {
  const c = uploader(async (url, opts) => {
    assert.equal(url, '/api/uploads'); assert.equal(opts.fields.kind, 'property_photo');
    assert.equal(opts.headers.Authorization, 'test-only'); assert.ok(opts.signal);
    return new Response(JSON.stringify({ id: 'file_123', url: '/api/files/file_123' }));
  });
  assert.equal((await c.upload()).id, 'file_123');
});
test('upload refuses malformed or foreign file references', async () => {
  for (const data of [{}, { id: 'x', url: 'https://other.test/photo' }, { id: '../x', url: '/api/files/../x' }]) {
    await assert.rejects(uploader(async () => new Response(JSON.stringify(data))).upload(), /Invalid upload response/);
  }
});
test('upload failures do not become successful photos or expose provider errors', async () => {
  await assert.rejects(uploader(async () => new Response('private provider details', { status: 500 })).upload(), /Upload unavailable/);
  await assert.rejects(uploader(async () => new Response(JSON.stringify({ detail: 'Invalid photo type' }), { status: 400 })).upload(), /Invalid photo type/);
});
test('upload refuses a response from a previous account session', async () => {
  const c = uploader(async () => { c.changeSession(); return new Response(JSON.stringify({ id: 'x', url: '/api/files/x' })); });
  await assert.rejects(c.upload(), /Session changed/);
});
function pickerHarness(results) {
  let slots = [], cursor = 0, photos = [], busy = [], calls = 0;
  const react = {
    useRef: value => { const i = cursor++; return slots[i] ??= { current: value }; },
    useState: value => { const i = cursor++; if (!(i in slots)) slots[i] = value; return [slots[i], next => { slots[i] = next; }]; },
    useEffect: () => {},
  };
  const jsx = (type, props) => ({ type, props });
  const ctx = { exports: {}, AbortController, setTimeout, clearTimeout, require: name => {
    if (name === 'react') return react;
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx };
    if (name === 'react-native') return { Platform: { OS: 'android' }, View: 'View', Text: 'Text', Pressable: 'Pressable' };
    if (name === 'expo-image-picker') return { launchImageLibraryAsync: async () => ({ canceled: false, assets: [{ uri: 'file:///a.jpg' }, { uri: 'file:///b.jpg' }] }) };
    if (name === '@/src/api') return { API_BASE: '/api', fileUrl: x => x, authHeaders: async () => ({}), getApiSessionVersion: () => 1 };
    if (name === '@/src/utils/upload') return { uploadForm: async () => { const result = results[calls++]; if (result instanceof Error) throw result; return new Response(JSON.stringify({ id: result, url: `/api/files/${result}` })); } };
    if (name === '@/src/theme') return { makeStyles: () => () => ({}), useTheme: () => ({ colors: {} }) };
    if (name === '@/src/i18n') return { useLang: () => ({ tx: x => x }) };
    if (name === '@/src/components/Toast') return { useToast: () => ({ show: () => {} }) };
    return {};
  }};
  vm.runInNewContext(source, ctx);
  const render = () => { cursor = 0; return ctx.exports.PhotoPicker({ photos, onChange: next => { photos = next; }, onBusyChange: value => busy.push(value) }); };
  function find(node, predicate) {
    if (!node || typeof node !== 'object') return;
    if (predicate(node)) return node;
    for (const child of [node.props?.children].flat(Infinity)) { const result = find(child, predicate); if (result) return result; }
  }
  return { render, find, get photos() { return photos; }, get busy() { return busy; }, get calls() { return calls; } };
}
test('partial upload retains successful photos and retries only failed selections', async () => {
  const h = pickerHarness(['a', new Error('offline'), 'b']);
  await h.find(h.render(), node => node.props?.testID === 'add-photo-btn').props.onPress();
  assert.deepEqual(Array.from(h.photos, p => p.id), ['a']);
  const retry = h.find(h.render(), node => node.type === 'Pressable' && node.props?.children?.props?.children === 'Retry failed uploads');
  assert.ok(retry);
  await retry.props.onPress();
  assert.deepEqual(Array.from(h.photos, p => p.id), ['a', 'b']);
  assert.equal(h.calls, 3);
  assert.deepEqual(h.busy, [true, false, true, false]);
});
test('uploaded photos can be reordered and removed without a new upload', async () => {
  const h = pickerHarness(['a', 'b']);
  await h.find(h.render(), node => node.props?.testID === 'add-photo-btn').props.onPress();
  h.find(h.render(), node => node.props?.accessibilityLabel === 'Move photo earlier').props.onPress();
  assert.deepEqual(Array.from(h.photos, p => p.id), ['b', 'a']);
  h.find(h.render(), node => node.props?.testID === 'photo-remove-0').props.onPress();
  assert.deepEqual(Array.from(h.photos, p => p.id), ['a']);
  assert.equal(h.calls, 2);
});
