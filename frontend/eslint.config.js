// https://docs.expo.dev/guides/using-eslint/
const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([
  expoConfig,
  {
    // Generated types and unmodified third-party source are not application code.
    ignores: ['dist/**', '.expo/**', 'scripts/cmd-guard/vendor/**'],
  },
  {
    files: ['tests/**/*.cjs'],
    languageOptions: { globals: { __dirname: 'readonly' } },
  },
]);
