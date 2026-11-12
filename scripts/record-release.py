"""Record exact local artifact identity; never claims deployment or prints environments."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def image_record(image, reference, commit, expected_id):
    if (image.get("Os")!="linux" or image.get("Id")!=expected_id or
        not re.fullmatch(r"sha256:[a-f0-9]{64}",expected_id or "") or
        (image.get("Config",{}).get("Labels") or {}).get("org.opencontainers.image.revision")!=commit):
        raise RuntimeError("Exact tested Linux artifact and revision label required")
    return {"tag":reference,"image_id":image["Id"],"repo_digests":image.get("RepoDigests",[]),
            "architecture":image.get("Architecture"),"os":image["Os"],"created":image.get("Created"),
            "revision":commit}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api",required=True)
    parser.add_argument("--web",required=True)
    parser.add_argument("--runtime-evidence",required=True,help="Successful exact-commit Linux result.json")
    parser.add_argument("--rollback-manifest",help="Previously verified compatible artifact manifest")
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    def git(*arguments): return subprocess.check_output(["git",*arguments],cwd=ROOT,text=True).strip()
    if git("status","--porcelain"): raise RuntimeError("Clean exact commit required")
    commit=git("rev-parse","HEAD")
    evidence_bytes=Path(args.runtime_evidence).read_bytes()
    evidence=json.loads(evidence_bytes)
    if evidence.get("status")!="PASS" or evidence.get("commit")!=commit or evidence.get("production") is not False:
        raise RuntimeError("Successful matching isolated runtime evidence required")
    images={}
    for name,reference in (("api",args.api),("web",args.web)):
        if not re.fullmatch(r"[^\s]+:"+commit,reference): raise RuntimeError("Full commit image tag required")
        result=subprocess.run(["docker","image","inspect","--format","{{json .}}",reference],capture_output=True,text=True,timeout=30)
        if result.returncode: raise RuntimeError("Image missing")
        image=json.loads(result.stdout)
        images[name]=image_record(image,reference,commit,evidence.get("images",{}).get("REHEARSAL_"+name.upper()+"_IMAGE"))
    manifest={"source_commit":commit,"recorded_at":datetime.now(timezone.utc).isoformat(),"images":images,
              "compose_sha256":hashlib.sha256((ROOT/"deploy/compose.production.yml").read_bytes()).hexdigest(),
              "caddy_sha256":hashlib.sha256((ROOT/"deploy/Caddyfile").read_bytes()).hexdigest(),
              "dependency_files":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
                  ("backend/requirements-production.txt","backend/requirements-production-constraints.txt","web/package-lock.json")},
              "runtime_evidence_sha256":hashlib.sha256(evidence_bytes).hexdigest(),
              "rehearsal_caddy_image":evidence.get("images",{}).get("REHEARSAL_CADDY_IMAGE"),
              "rollback_manifest":args.rollback_manifest,"runtime_acceptance":"Matching isolated evidence; production/EC2 NOT VERIFIED"}
    path=Path(args.output).resolve()
    if ROOT/".cache" not in path.parents: raise RuntimeError("Output must be under repository .cache")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print("PASS artifact identity recorded; review manifest, scans and runtime evidence separately")


if __name__=="__main__":
    try: main()
    except Exception:
        print("BLOCKED artifact record; clean commit, exact Linux images and safe output required")
        raise SystemExit(1)
