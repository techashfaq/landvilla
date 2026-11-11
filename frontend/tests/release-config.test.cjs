const test = require('node:test');
const assert = require('node:assert/strict');
const configure = require('../app.config.js');
test('release config rejects missing, local, credentialed and HTTP endpoints', () => {
  const original = { ...process.env };
  try {
    process.env.EAS_BUILD_PROFILE = 'production';
    for (const url of ['', 'http://api.example', 'https://localhost', 'https://127.0.0.1', 'https://user:pass@api.example']) {
      process.env.EXPO_PUBLIC_BACKEND_URL = url;
      assert.throws(() => configure({ config: {} }));
    }
    process.env.EXPO_PUBLIC_BACKEND_URL = 'https://api.example';
    const result = configure({ config: { version: '1.0.0', plugins: ['existing'] } });
    assert.equal(result.android.package, 'com.landvilla.app');
    assert.equal(result.android.versionCode, 1);
    assert.deepEqual(result.plugins, ['existing']);
  } finally { process.env = original; }
});
