"""Disposable GitHub-hosted Linux runtime campaign. Refuses EC2/ordinary operator hosts.

No production credentials, image publication, real domain, or provider access.
Docker resources created by this script have the fixed landvilla-rehearsal label.
"""
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/".cache/linux-rehearsal"
ENV={k:v for k,v in os.environ.items() if k in ("PATH","HOME","LANG")}
ENV["COMPOSE_DISABLE_ENV_FILE"]="1"


def run(command, *, capture=True):
    result=subprocess.run(command,cwd=ROOT,env=ENV,capture_output=capture,text=True,timeout=600,check=False)
    if result.returncode:
        # curl targets are fixed HTTPS localhost URLs with no credentials/query.
        # Preserve its TLS/connection diagnostic, never arbitrary command output.
        if command[0]=="curl" and result.stderr:
            print(result.stderr.strip(),flush=True)
        raise RuntimeError("Command failed: "+command[0]+" "+command[1]+" exit="+str(result.returncode))
    return result.stdout.strip() if capture else ""


def main():
    if os.getenv("GITHUB_ACTIONS")!="true" or os.getenv("RUNNER_ENVIRONMENT")!="github-hosted" or sys.platform!="linux":
        raise RuntimeError("Dedicated GitHub-hosted Linux runner required")
    if run(["git","status","--porcelain"]): raise RuntimeError("Clean checkout required")
    commit=run(["git","rev-parse","HEAD"])
    if commit!=os.environ["GITHUB_SHA"]: raise RuntimeError("Exact workflow commit required")
    WORK.mkdir(parents=True,exist_ok=True)
    spec=importlib.util.spec_from_file_location("checker",ROOT/"scripts/check-rehearsal.py")
    checker=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    selected=[]
    # Candidates are selected only AFTER read-only comparison with actual local
    # routes/networks on this new disposable runner, never copied to EC2.
    for second in range(20,31):
        candidate=ipaddress.IPv4Network(f"172.{second}.240.0/24")
        try: checker.host_collisions(candidate)
        except ValueError: continue
        selected.append(candidate)
        if len(selected)==2: break
    if len(selected)!=2: raise RuntimeError("Two collision-free runner allocations required")
    backend_subnet,ingress_subnet=selected
    manifest=json.loads((ROOT/"deploy/reviewed-base-images.json").read_text())
    images={r["repository"]:r["repository"]+":"+r["tag"]+"@"+r["digest"] for r in manifest["images"]}
    settings={"REHEARSAL_SUBNET":str(backend_subnet),"REHEARSAL_INGRESS_SUBNET":str(ingress_subnet),
              "REHEARSAL_DYNAMIC_RANGE":str(list(backend_subnet.subnets(new_prefix=25))[1]),
              "REHEARSAL_WEB_IP":str(backend_subnet.network_address+10),"REHEARSAL_MONGO_IMAGE":images["library/mongo"],
              "REHEARSAL_MAIL_IMAGE":images["axllent/mailpit"],"REHEARSAL_CADDY_IMAGE":images["library/caddy"]}
    versions={"docker_engine":run(["docker","version","--format","{{.Server.Version}}"]),
              "compose":run(["docker","compose","version","--short"])}
    artifacts={}
    contexts={"api":"backend","web":"web","caddy":"deploy/images/caddy","mongo":"deploy/images/mongo"}
    parents={"api":"library/python","web":"library/node","caddy":"library/caddy","mongo":"library/mongo"}
    for name,context in contexts.items():
        tag=f"landvilla-{name}:{commit}"
        run(["docker","build","--label","org.opencontainers.image.revision="+commit,
             "--label","org.landvilla.base-image="+images[parents[name]],"-t",tag,context],capture=False)
        settings["REHEARSAL_"+name.upper()+"_IMAGE"]=run(["docker","image","inspect","--format","{{.Id}}",tag])
        metadata=json.loads(run(["docker","image","inspect","--format","{{json .}}",tag]))
        artifacts[name]={key:metadata.get(key) for key in ("Id","Size","Os","Architecture","Created")}
        artifacts[name]["revision"]=(metadata.get("Config",{}).get("Labels") or {}).get("org.opencontainers.image.revision")
        artifacts[name]["base"]=(metadata.get("Config",{}).get("Labels") or {}).get("org.landvilla.base-image")
        if artifacts[name]["Os"]!="linux" or artifacts[name]["Architecture"]!="amd64" or artifacts[name]["revision"]!=commit:
            raise RuntimeError("Linux source artifact mismatch")
    candidate_file=WORK/"candidate-images.json"
    candidate_file.write_text(json.dumps(artifacts,indent=2)+"\n")
    env_file=WORK/"rehearsal.env"
    env_file.write_text("\n".join(k+"="+v for k,v in settings.items())+"\n")
    model=checker.resolve(env_file)
    checker.validate(model,artifacts,commit)
    compose=["docker","compose","--env-file",str(env_file),"-f","deploy/compose.rehearsal.yml"]
    started=False
    completed=False
    phase="startup"
    checks=[]
    runtime_versions={}
    try:
        started=True
        run(compose+["up","-d","--wait","--wait-timeout","180"],capture=False)
        checks.append("startup and liveness")
        phase="readiness and proxy source"
        run(compose+["exec","-T","web","node","-e","fetch('http://127.0.0.1:3000/ready').then(r=>process.exit(r.status===200?0:1)).catch(()=>process.exit(1))"])
        checks.append("API Mongo topology/storage mock readiness through Web")
        connection=subprocess.Popen(compose+["exec","-T","web","node","-e",
            "const s=require('node:net').createConnection({host:'api',port:8000}); s.on('error',()=>process.exit(1)); setTimeout(()=>s.end(),15000)"],
            cwd=ROOT,env=ENV,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            time.sleep(1)
            probe="import socket,json; from pathlib import Path; print(json.dumps([socket.inet_ntoa(bytes.fromhex(p[2].split(':')[0])[::-1]) for l in Path('/proc/net/tcp').read_text().splitlines()[1:] if len(p:=l.split())>3 and p[1].endswith(':1F40') and p[3]=='01']))"
            observed=json.loads(run(compose+["exec","-T","api","python","-c",probe]))
            if settings["REHEARSAL_WEB_IP"] not in observed: raise RuntimeError("API-observed Web source mismatch")
            checks.append("actual API TCP Web source observed on ephemeral runner")
        finally:
            connection.terminate()
            connection.wait(timeout=10)
        negative="import urllib.request,urllib.error; r=urllib.request.Request('http://api:8000/api/',headers={'X-Forwarded-Proto':'https','X-Forwarded-For':'"+settings["REHEARSAL_WEB_IP"]+"'});\ntry: urllib.request.urlopen(r,timeout=3); raise SystemExit(1)\nexcept urllib.error.HTTPError as e: raise SystemExit(0 if e.code==400 else 1)"
        run(compose+["exec","-T","storage","python","-c",negative])
        checks.append("untrusted fixture peer cannot forge HTTPS proxy trust")
        phase="runtime hardening"
        for name in ("api","web","caddy","mongo","storage","mail"):
            container=run(compose+["ps","-q",name])
            config=json.loads(run(["docker","inspect","--format","{{json .HostConfig}}",container]))
            if not config["ReadonlyRootfs"] or "ALL" not in config["CapDrop"] or config["Memory"]<=0:
                raise RuntimeError("Runtime hardening mismatch")
            user=run(["docker","inspect","--format","{{.Config.User}}",container])
            if user in ("","0","root","0:0"): raise RuntimeError("Root runtime")
            if name!="caddy" and config.get("PortBindings"): raise RuntimeError("Application published")
        checks.append("non-root/read-only/dropped capabilities/resource/port declarations effective")
        if not run(compose+["exec","-T","caddy","caddy","version"]).startswith("v2.11.9 "):
            raise RuntimeError("Supported Caddy binary changed")
        run(compose+["exec","-T","web","node","-e",
            "const fs=require('fs'); for(const p of ['/usr/local/lib/node_modules/npm','/usr/local/bin/npm','/usr/local/bin/npx','/usr/local/bin/yarn']){if(fs.existsSync(p))process.exit(1)}"])
        run(compose+["exec","-T","api","python","-m","pip","check"])
        runtime_versions["node"]=json.loads(run(compose+["exec","-T","web","node","-p","JSON.stringify(process.versions)"]))
        runtime_versions["python"]=run(compose+["exec","-T","api","python","-c","import platform; print(platform.python_version())"])
        runtime_versions["mongo_yaml"]=run(compose+["exec","-T","mongo","mongosh","--quiet","--nodb","--eval",
            "const fs=require('fs'); if(fs.realpathSync('/js-yaml.js')!=='/opt/js-yaml/dist/js-yaml.js') quit(1); const yaml=require('/js-yaml.js'); if(yaml.load('fixture: true').fixture!==true) quit(1); for(const p of ['/usr/local/bin/gosu','/usr/bin/bsondump','/usr/bin/mongodump','/usr/bin/mongoexport','/usr/bin/mongofiles','/usr/bin/mongoimport','/usr/bin/mongorestore','/usr/bin/mongostat','/usr/bin/mongotop']){if(fs.existsSync(p)) quit(1)} print(require('/opt/js-yaml/package.json').version)"])
        if runtime_versions["mongo_yaml"]!="3.15.2": raise RuntimeError("Patched YAML helper required")
        checks.append("supported Caddy version, unused Web package managers absent, API pip check")
        phase="TLS and synthetic browser flow"
        # Read the public certificate in the container's mount namespace. docker cp
        # failed for this tmpfs-backed fixture; never copy its CA private key.
        public_ca=run(compose+["exec","-T","caddy","cat","/data/caddy/pki/authorities/local/root.crt"])
        from cryptography import x509
        certificate=x509.load_pem_x509_certificate(public_ca.encode())
        if not certificate.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise RuntimeError("Rehearsal root certificate required")
        (WORK/"rehearsal-ca.crt").write_text(public_ca+"\n")
        # Trust only this disposable CA for this command; no host trust-store changes.
        run(["curl","--fail","--silent","--show-error","--retry","5","--retry-delay","3","--cacert",str(WORK/"rehearsal-ca.crt"),"https://localhost:8443/"])
        checks.append("loopback real TLS with explicit disposable CA")
        smoke=[sys.executable,"scripts/smoke-rehearsal.py","--env-file",str(env_file),"--ca",str(WORK/"rehearsal-ca.crt"),"--candidate-images",str(candidate_file)]
        run(smoke,capture=False)
        checks.append("browser OTP/CSRF/logout and private media synthetic acceptance")
        phase="dependency failure and restart recovery"
        run(compose+["stop","storage"])
        run(compose+["exec","-T","web","node","-e","fetch('http://127.0.0.1:3000/ready').then(r=>process.exit(r.status===503?0:1))"])
        run(compose+["start","storage"])
        for attempt in range(20):
            try:
                run(compose+["exec","-T","web","node","-e","fetch('http://127.0.0.1:3000/ready').then(r=>process.exit(r.status===200?0:1))"])
                break
            except RuntimeError: time.sleep(1)
        else: raise RuntimeError("Readiness recovery failed")
        checks.append("storage failure/recovery")
        run(compose+["restart","api","web"])
        run(compose+["up","-d","--wait","--wait-timeout","120"],capture=False)
        run(compose+["exec","-T","web","node","-e","fetch('http://127.0.0.1:3000/ready').then(r=>process.exit(r.status===200?0:1)).catch(()=>process.exit(1))"])
        run(["curl","--fail","--silent","--show-error","--retry","5","--retry-delay","3","--cacert",str(WORK/"rehearsal-ca.crt"),"https://localhost:8443/api/meta"])
        run(smoke+["--existing-account"],capture=False)
        checks.append("same-artifact restart recovery; not previous-release rollback")
        completed=True
    except Exception:
        print("FAIL phase: "+phase,flush=True)
        # Fixed metadata only. Never broad docker inspect, environment, health
        # output, request bodies, OTP messages or application logs.
        for name in ("mongo","storage","prepare","mail","api","web","caddy"):
            try:
                container=run(compose+["ps","-aq",name])
                if container:
                    state=run(["docker","inspect","--format",'{{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}{{if .State.Health}} health={{.State.Health.Status}}{{end}}',container])
                    print(name+": "+state,flush=True)
            except Exception: print(name+": diagnostic unavailable",flush=True)
        raise
    finally:
        if started: run(compose+["down","--volumes","--remove-orphans"],capture=False)
        if completed: checks.append("disposable project containers/network/volumes cleanup completed")
        (WORK/"result.json").write_text(json.dumps({"commit":commit,"status":"PASS" if completed else "FAIL","checks_passed":checks,"images":settings,
            "tool_versions":versions,"runtime_versions":runtime_versions,"artifacts":artifacts,"production":False,
            "directional_isolation":"NOT TESTED / not implemented","previous_release_rollback":"BLOCKED no known-good artifact"},indent=2)+"\n")
    print("PASS disposable Linux runtime campaign; production/EC2 acceptance remains separate")


if __name__=="__main__":
    try: main()
    except Exception as error:
        print("FAIL disposable runtime campaign: "+str(error))
        raise SystemExit(1)
