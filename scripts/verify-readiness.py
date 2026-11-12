"""Credential-isolated local verification. No live suites, deployment or dotenv reads."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True, help="Isolated requirements-test interpreter")
    parser.add_argument("--compose", required=True, help="Verified Compose executable")
    parser.add_argument("--caddy", required=True, help="Verified Caddy executable")
    parser.add_argument("--stage", choices=("backend", "web", "deploy", "build", "syntax"), required=True)
    args=parser.parse_args()
    work=ROOT/".cache/master-readiness"
    work.mkdir(exist_ok=True)
    (work/"tmp").mkdir(exist_ok=True)
    env={k:v for k,v in os.environ.items() if k.upper() in {"PATH","SYSTEMROOT","WINDIR","COMSPEC","PATHEXT","NUMBER_OF_PROCESSORS"}}
    env.update({k:str(work/"tmp") for k in ("TEMP","TMP","TMPDIR","HOME","USERPROFILE","APPDATA","LOCALAPPDATA")})
    env.update(PYTHON_DOTENV_DISABLED="1",PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PIP_CONFIG_FILE=os.devnull,
               PIP_DISABLE_PIP_VERSION_CHECK="1",NEXT_TELEMETRY_DISABLED="1",COMPOSE_DISABLE_ENV_FILE="1",
               LANDVILLA_TEST_COMPOSE_BINARY=str(Path(args.compose).resolve()), CADDY_BINARY=str(Path(args.caddy).resolve()))
    node="node"
    commands={
      "backend":[("pip-check",[args.python,"-m","pip","check"],ROOT),
                 ("backend-tests",[args.python,"-m","unittest","discover","-s","tests/unit","-v"],ROOT/"backend")],
      "web":[("web-tests",[node,"--test",*map(str,sorted((ROOT/"web/tests").glob("*.test.ts")))],ROOT/"web"),
             ("web-lint",[node,"node_modules/eslint/bin/eslint.js",".","--max-warnings","0"],ROOT/"web"),
             ("web-types",[node,"node_modules/typescript/bin/tsc","--noEmit","--incremental","false"],ROOT/"web")],
      "build":[("web-build",[node,"scripts/verify-production-build.mjs"],ROOT/"web")],
      "deploy":[("deployment-tests",[args.python,"-m","unittest","discover","-s","tests","-p","test_*.py","-v"],ROOT)],
      "syntax":[("python-compilation",[args.python,"-m","compileall","-q","backend","scripts","deploy/rehearsal","tests"],ROOT)]}
    failed=False
    for label,command,cwd in commands[args.stage]:
        start=time.monotonic()
        with (work/(label+".log")).open("w",encoding="utf-8") as log:
            result=subprocess.run(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,check=False)
        record={"command":command,"cwd":str(cwd),"exit_code":result.returncode,"seconds":round(time.monotonic()-start,3)}
        (work/(label+"-command.json")).write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
        print(label, "PASS" if result.returncode==0 else "FAIL",record["seconds"],flush=True)
        failed |= result.returncode!=0
    return int(failed)


if __name__=="__main__": raise SystemExit(main())
