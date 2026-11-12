"""Synthetic acceptance only for validated disposable localhost rehearsal."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--env-file",required=True)
    p.add_argument("--ca",required=True)
    args=p.parse_args()
    spec=importlib.util.spec_from_file_location("checker",ROOT/"scripts/check-rehearsal.py")
    checker=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    model=checker.resolve(Path(args.env_file).resolve())
    checker.validate(model)
    compose=["docker","compose","--env-file",str(Path(args.env_file).resolve()),"-f",str(ROOT/"deploy/compose.rehearsal.yml")]
    env={k:v for k,v in os.environ.items() if k in ("PATH","HOME","LANG")}
    env["COMPOSE_DISABLE_ENV_FILE"]="1"
    origin="https://localhost:8443"
    context=ssl.create_default_context(cafile=args.ca)
    with httpx.Client(base_url=origin,verify=context,trust_env=False,follow_redirects=False,timeout=30) as client:
        def expected(response,status,label):
            if response.status_code!=status: raise RuntimeError(label+" status "+str(response.status_code))
            return response
        for route in ("/","/properties","/buy","/rent","/contact","/faq","/robots.txt","/sitemap.xml"):
            expected(client.get(route),200,"public route")
        for route in ("/health","/ready"): expected(client.get(route),404,"hidden probes")
        meta=expected(client.get("/api/meta"),200,"public reference data").json()
        if meta.get("city",{}).get("id")!="city_rehearsal": raise RuntimeError("Synthetic city fixture missing")
        expected(client.get("/api/properties",params={"purpose":"buy","sort":"newest","page":1}),200,"public discovery")
        bootstrap=expected(client.get("/api/auth/browser/bootstrap",headers={"Origin":origin}),200,"bootstrap")
        cookie=bootstrap.headers.get("set-cookie","").lower()
        if not all(x in cookie for x in ("__host-lv_session=","secure","httponly","samesite=lax")): raise RuntimeError("cookie attributes")
        headers={"Origin":origin,"X-CSRF-Token":bootstrap.json()["csrf_token"]}
        expected(client.post("/api/auth/logout",headers={"Origin":"https://untrusted.invalid"},json={}),403,"origin rejection")
        expected(client.post("/api/auth/logout",headers={"Origin":origin},json={}),403,"CSRF rejection")
        challenge=expected(client.post("/api/auth/otp/request",headers=headers,json={"identifier":"rehearsal@example.com","purpose":"register",
            "registration":{"first_name":"Rehearsal","last_name":"Fixture","email":"rehearsal@example.com","mobile":"+919999999991","account_role":"owner","accept_terms":True,"accept_privacy":True}}),200,"OTP registration")
        # The local catcher's message is consumed in memory, never printed or archived.
        mail_code="import urllib.request; print(urllib.request.urlopen('http://mail:8025/api/v1/message/latest/raw',timeout=3).read().decode())"
        result=subprocess.run(compose+["exec","-T","api","python","-c",mail_code],env=env,capture_output=True,text=True,timeout=10)
        match=re.search(r"\b([0-9]{6})\b",result.stdout)
        if result.returncode or not match: raise RuntimeError("Local synthetic OTP delivery")
        verified=expected(client.post("/api/auth/otp/verify",headers=headers,json={"challenge_id":challenge.json()["challenge_id"],"code":match.group(1)}),200,"OTP verification")
        headers["X-CSRF-Token"]=verified.json()["csrf_token"]
        if "session_token" in verified.json(): raise RuntimeError("Browser bearer exposure")
        expected(client.get("/api/auth/me"),200,"authenticated profile")
        expected(client.get("/api/admin/stats"),403,"admin role denial")
        payload=b"%PDF-1.4\nsynthetic private document fixture\n%%EOF"
        upload=expected(client.post("/api/uploads",headers=headers,data={"kind":"broker_doc"},files={"file":("fixture.pdf",payload,"application/pdf")}),200,"private upload")
        path=upload.json()["url"]
        if not re.fullmatch(r"/api/files/[a-zA-Z0-9_-]{1,100}",path): raise RuntimeError("fixed private media path")
        media=expected(client.get(path),200,"owner media")
        if media.content!=payload or "no-store" not in media.headers.get("cache-control",""): raise RuntimeError("private media response")
        with httpx.Client(base_url=origin,verify=context,trust_env=False) as anonymous:
            if anonymous.get(path).status_code not in (401,403,404): raise RuntimeError("private media disclosed")
        expected(client.post("/api/auth/logout",headers=headers,json={}),200,"logout")
        expected(client.get("/api/auth/me"),401,"session revoked")
    print("PASS synthetic loopback TLS public/auth/CSRF/admin-denial/private-media/logout flow")


if __name__=="__main__":
    try: main()
    except Exception as error:
        # Our RuntimeError messages contain only fixed check labels and HTTP status.
        # Network/provider exceptions remain type-only; never print bodies/URLs/OTP.
        detail=str(error) if type(error) is RuntimeError else type(error).__name__
        print("FAIL rehearsal smoke: "+detail+"; no response bodies or credentials emitted")
        raise SystemExit(1)
