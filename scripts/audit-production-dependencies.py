"""Public registry advisory observations for exact pinned Python and Web runtime packages."""
import concurrent.futures
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def request(url,payload=None):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    data=None if payload is None else json.dumps(payload).encode()
    with opener.open(urllib.request.Request(url,data=data,headers={"Content-Type":"application/json","User-Agent":"LANDVILLA-dependency-review"}),timeout=30) as response:
        return json.load(response)


def main():
    pins=[]
    for name in ("requirements-production.txt","requirements-production-constraints.txt"):
        for line in (ROOT/"backend"/name).read_text(encoding="utf-8").splitlines():
            if re.fullmatch(r"[A-Za-z0-9_-]+==[A-Za-z0-9.+_-]+",line): pins.append(line.split("=="))
    def check(pin):
        name,version=pin
        url=f"https://pypi.org/pypi/{name}/{version}/json"
        metadata=request(url)
        return {"name":name,"version":version,"source":url,"yanked":metadata["info"]["yanked"],
                "advisories":[v for v in metadata.get("vulnerabilities",[]) if not v.get("withdrawn")]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: records=list(pool.map(check,pins))
    lock=json.loads((ROOT/"web/package-lock.json").read_text(encoding="utf-8"))
    packages={}
    for path,info in lock["packages"].items():
        if path and not info.get("dev") and info.get("version"):
            name=info.get("name") or path.rsplit("node_modules/",1)[-1]
            packages.setdefault(name,[]).append(info["version"])
    npm=request("https://registry.npmjs.org/-/npm/v1/security/advisories/bulk",packages)
    result={"retrieved_at":datetime.now(timezone.utc).isoformat(),"python":records,"npm_package_names":len(packages),"npm_advisories":npm}
    out=ROOT/".cache/master-readiness"
    out.mkdir(exist_ok=True)
    (out/"dependency-advisories.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    count=sum(len(r["advisories"]) for r in records)+sum(len(v) for v in npm.values())
    yanked=sum(bool(r["yanked"]) for r in records)
    print(f"{'PASS' if not count and not yanked else 'FAIL'} dated registry observation: {len(records)} Python pins, {len(packages)} Web runtime names, {count} advisories, {yanked} yanked pins")
    return int(bool(count or yanked))


if __name__=="__main__":
    try: raise SystemExit(main())
    except (OSError,ValueError,KeyError):
        print("BLOCKED public advisory metadata unavailable; no clearance claimed")
        raise SystemExit(1)
