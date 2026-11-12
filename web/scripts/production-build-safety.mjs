import { existsSync, readdirSync, statSync } from "node:fs";
import { basename, resolve } from "node:path";

export function copyBuildEntry(entry) {
  return !basename(entry).toLowerCase().startsWith(".env");
}

export function verificationEnvironment(input, temporary) {
  // Build-time NEXT_PUBLIC_* variables can be embedded into client code. Do not
  // inherit operator/application secrets, Node hooks, proxy settings or npm tokens.
  const allowed = new Set(["PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "NUMBER_OF_PROCESSORS"]);
  return {
    ...Object.fromEntries(Object.entries(input).filter(([name]) => allowed.has(name.toUpperCase()))),
    NODE_ENV: "production", WEB_ORIGIN: "https://landvilla.in", BACKEND_ORIGIN: "http://api:8000", BACKEND_TRANSPORT: "private-http",
    NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID: "", NEXT_TELEMETRY_DISABLED: "1", TEMP: temporary, TMP: temporary, TMPDIR: temporary,
    HOME: temporary, USERPROFILE: temporary, APPDATA: temporary, LOCALAPPDATA: temporary,
    XDG_CONFIG_HOME: temporary, XDG_CACHE_HOME: temporary, NODE_COMPILE_CACHE: resolve(temporary, "compile"),
  };
}

export function assertStandaloneArtifact(directory) {
  for (const name of ["server.js", "package.json", ".next/BUILD_ID", ".next/routes-manifest.json"]) {
    const path = resolve(directory, name);
    if (!existsSync(path) || !statSync(path).isFile()) throw new Error("Standalone build is missing a required runtime file.");
  }
  for (const name of ["public", ".next/static"]) {
    const path = resolve(directory, name);
    if (!existsSync(path) || !statSync(path).isDirectory()) throw new Error("Standalone build is missing its asset directory.");
  }
  if (!readdirSync(resolve(directory, ".next/static")).length) throw new Error("Standalone static assets are empty.");
}
