"""Scan existing disposable CI images; never publishes images or contacts production."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/".cache/linux-rehearsal"
VERSION="0.121.3"
# Observed from authoritative GitHub release asset metadata on 2026-11-12.
ARCHIVE_SHA256="e9da18cc1429e786722e32161288103600efffd8e483c90761f90485bd1bec85"


def main():
    if os.getenv("GITHUB_ACTIONS")!="true" or os.getenv("RUNNER_ENVIRONMENT")!="github-hosted" or sys.platform!="linux":
        raise RuntimeError("Disposable hosted Linux runner required")
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--result",required=True,type=Path)
    args=p.parse_args()
    result=json.loads(args.result.read_text())
    if result.get("production") is not False: raise RuntimeError("Disposable evidence required")
    archive=WORK/"grype.tar.gz"
    with urllib.request.urlopen(f"https://github.com/anchore/grype/releases/download/v{VERSION}/grype_{VERSION}_linux_amd64.tar.gz",timeout=60) as response:
        data=response.read(100*1024*1024)
    if hashlib.sha256(data).hexdigest()!=ARCHIVE_SHA256: raise RuntimeError("Scanner checksum mismatch")
    archive.write_bytes(data)
    binary=WORK/"grype"
    with tarfile.open(archive,"r:gz") as bundle:
        member=bundle.getmember("grype")
        if not member.isfile() or member.size>200*1024*1024: raise RuntimeError("Invalid scanner archive")
        binary.write_bytes(bundle.extractfile(member).read())
    binary.chmod(0o700)
    env={k:v for k,v in os.environ.items() if k in ("PATH","HOME","LANG")}
    env.update(GRYPE_CHECK_FOR_APP_UPDATE="false",GRYPE_DB_CACHE_DIR=str(WORK/"grype-db"))
    findings=[]
    for name in ("API","WEB","CADDY","MONGO","MAIL"):
        reference=result["images"]["REHEARSAL_"+name+"_IMAGE"]
        process=subprocess.run([str(binary),"docker:"+reference,"-o","json"],cwd=WORK,env=env,capture_output=True,text=True,timeout=600)
        if process.returncode: raise RuntimeError("Scanner execution failed for "+name)
        report=json.loads(process.stdout)
        records=[]
        for match in report.get("matches",[]):
            vulnerability=match["vulnerability"]
            package=match["artifact"]
            records.append({"id":vulnerability["id"],"severity":vulnerability["severity"],
                "package":package["name"],"installed":package["version"],
                "fix":vulnerability.get("fix"),"source":vulnerability.get("dataSource")})
        findings.append({"image":name,"reference":reference,"matches":records,
                         "database":report.get("descriptor",{}).get("db",{})})
        print(name+": "+str(len(records))+" vulnerability matches; triage required",flush=True)
    blocked=any(m["severity"] in ("High","Critical") for item in findings for m in item["matches"])
    (WORK/"image-security.json").write_text(json.dumps({"commit":result["commit"],"scanner":"grype "+VERSION,
        "scanner_archive_sha256":ARCHIVE_SHA256,"status":"FAIL" if blocked else "PASS","images":findings},indent=2)+"\n")
    return int(blocked)


if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as error:
        print("BLOCKED image security scan: "+type(error).__name__+"; no configuration/output bodies emitted")
        raise SystemExit(1)
