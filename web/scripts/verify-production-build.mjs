// Reproducible build validation without reading, moving or copying local .env files.
import { cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { copyBuildEntry, verificationEnvironment, assertStandaloneArtifact } from "./production-build-safety.mjs";

const source = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const cache = resolve(source, "../.cache");
mkdirSync(cache, { recursive: true });
const stage = mkdtempSync(resolve(cache, "web-production-build-"));
// Copy dependencies rather than symlinking: Turbopack requires dependencies
// inside its project root. No installs, containers or provider requests.
for (const name of ["src", "scripts", "package.json", "package-lock.json", "next.config.ts", "tsconfig.json", "node_modules"]) {
  cpSync(resolve(source, name), resolve(stage, name), { recursive: true, dereference: true, filter: copyBuildEntry });
}
if (existsSync(resolve(source, "public"))) cpSync(resolve(source, "public"), resolve(stage, "public"), { recursive: true, filter: copyBuildEntry });
mkdirSync(resolve(stage, "public"), { recursive: true });
const temporary = resolve(stage, "tmp");
mkdirSync(temporary);
if (readdirSync(stage).some(name => name.startsWith(".env"))) throw new Error("Verification must not contain environment files.");
const env = verificationEnvironment(process.env, temporary);
console.log(`Isolated production build: ${stage}`);
for (const args of [[resolve(stage, "node_modules/next/dist/bin/next"), "build"], [resolve(stage, "scripts/prepare-standalone.mjs")]]) {
  const result = spawnSync(process.execPath, args, { cwd: stage, env, stdio: "inherit" });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
assertStandaloneArtifact(resolve(stage, ".next/standalone"));
console.log(`Verified standalone artifact: ${resolve(stage, ".next/standalone")}`);
