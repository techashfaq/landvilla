"""Verify public pinned image manifests. No image execution or production access."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def verified_manifest(data, expected, reported):
    actual="sha256:"+hashlib.sha256(data).hexdigest()
    if actual!=expected or actual!=reported:
        raise ValueError("Manifest content digest mismatch")
    document=json.loads(data)
    targets=[m for m in document.get("manifests",[]) if m.get("platform",{}).get("os")=="linux"
             and m["platform"].get("architecture")=="amd64"]
    if len(targets)!=1:
        raise ValueError("Unique Linux amd64 image required")
    return targets[0]["digest"]


def main():
    if os.getenv("GITHUB_ACTIONS")!="true" or os.getenv("RUNNER_ENVIRONMENT")!="github-hosted" or sys.platform!="linux":
        raise RuntimeError("Disposable hosted Linux runner required")
    records=[]
    for image in json.loads((ROOT/"deploy/reviewed-base-images.json").read_text())["images"]:
        repository=image["repository"]
        headers={"Accept":"application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json"}
        if repository=="gcr.io/distroless/nodejs24-debian13":
            url="https://gcr.io/v2/distroless/nodejs24-debian13/manifests/"+image["digest"]
        elif re.fullmatch(r"(?:library|axllent)/[a-z0-9-]+",repository):
            # Anonymous, read-only registry bearer. Never output/store its value.
            with urllib.request.urlopen("https://auth.docker.io/token?service=registry.docker.io&scope=repository:"+repository+":pull",timeout=30) as response:
                token=json.load(response)["token"]
            headers["Authorization"]="Bearer "+token
            url="https://registry-1.docker.io/v2/"+repository+"/manifests/"+image["digest"]
        else:
            raise ValueError("Unreviewed base registry")
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as response:
            data=response.read(4*1024*1024)
            platform=verified_manifest(data,image["digest"],response.headers.get("Docker-Content-Digest"))
        records.append({"repository":repository,"tag":image["tag"],"digest":image["digest"],
                        "linux_amd64_manifest":platform,"body_sha256":hashlib.sha256(data).hexdigest()})
    out=ROOT/".cache/linux-rehearsal/base-manifests.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"commit":os.environ["GITHUB_SHA"],"verified":records},indent=2)+"\n")
    print("PASS pinned manifest content and Linux amd64 selection: "+str(len(records))+" inputs")


if __name__=="__main__":
    try: main()
    except Exception as error:
        print("BLOCKED image input verification: "+type(error).__name__+"; registry response/credentials withheld")
        raise SystemExit(1)
