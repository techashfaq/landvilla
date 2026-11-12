import { cpSync, existsSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { copyBuildEntry, assertStandaloneArtifact } from "./production-build-safety.mjs";

const target = resolve(".next/standalone");
mkdirSync(resolve(target, "public"), { recursive: true });
if (existsSync("public")) cpSync("public", resolve(target, "public"), { recursive: true, filter: copyBuildEntry });
cpSync(".next/static", resolve(target, ".next/static"), { recursive: true });
assertStandaloneArtifact(target);
