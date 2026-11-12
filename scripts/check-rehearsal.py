"""Validate disposable declarations; optional read-only host collision check. Prints no values."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from production_runtime import validate_environment


def require(value,label):
    if not value: raise ValueError(label)


def resolve(env_file,binary=None):
    env={k:v for k,v in os.environ.items() if k.upper() in {"PATH","SYSTEMROOT","WINDIR","COMSPEC","PATHEXT","HOME","USERPROFILE"}}
    env["COMPOSE_DISABLE_ENV_FILE"]="1"
    command=([binary] if binary else ["docker","compose"])+["--env-file",str(env_file),"-f",str(ROOT/"deploy/compose.rehearsal.yml"),"config","--format","json"]
    result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=30,check=False)
    require(result.returncode==0,"rehearsal interpolation")
    return json.loads(result.stdout)


def validate(model):
    require(model.get("name")=="landvilla-rehearsal","unique rehearsal project")
    services=model.get("services",{})
    require(set(services)=={"api","web","caddy","mongo","storage","prepare","mail"},"exact rehearsal services")
    network=model.get("networks",{}).get("rehearsal",{})
    require(set(model.get("networks",{}))=={"rehearsal"} and network.get("internal") is True and
            network.get("driver")=="bridge" and not network.get("enable_ipv6") and not network.get("external"),"internal owned IPv4 rehearsal network")
    allocation=network["ipam"]["config"]
    require(len(allocation)==1,"one allocation")
    subnet=ipaddress.IPv4Network(allocation[0]["subnet"],strict=True)
    pool=ipaddress.IPv4Network(allocation[0]["ip_range"],strict=True)
    peer=ipaddress.IPv4Address(services["web"]["networks"]["rehearsal"]["ipv4_address"])
    require(any(subnet.subnet_of(ipaddress.IPv4Network(n)) for n in ("10.0.0.0/8","172.16.0.0/12","192.168.0.0/16")),"private subnet")
    require(pool.subnet_of(subnet) and pool!=subnet and pool.num_addresses>=16 and peer in subnet and peer not in pool and
            peer not in (subnet.network_address,subnet.network_address+1,subnet.broadcast_address),"reserved peer outside dynamic pool")
    for name,service in services.items():
        require(service.get("read_only") is True and service.get("restart")=="no" and service.get("user") in ("10001:10001","1000:1000","999:999"),"disposable nonroot runtime")
        require(service.get("cap_drop")==["ALL"] and not service.get("cap_add") and
                "no-new-privileges:true" in service.get("security_opt",[]),"dropped privileges")
        require(not any(service.get(k) for k in ("privileged","network_mode","devices","env_file","secrets","configs","build","extra_hosts","external_links","container_name","entrypoint","volumes_from","use_api_socket","pid")),"no external runtime inputs")
        expected_commands={"mongo":["mongod","--replSet","lv_rehearsal","--bind_ip_all"],
            "storage":["python","/rehearsal/storage_mock.py"],"prepare":["python","/rehearsal/prepare.py"],
            "caddy":["caddy","run","--config","/etc/caddy/Caddyfile","--adapter","caddyfile"]}
        require(service.get("command")==expected_commands.get(name),"reviewed rehearsal command")
        require(set(service["networks"])=={"rehearsal"},"no alternate network")
        require(float(service.get("cpus",0))>0 and int(service.get("mem_limit",0))>0 and int(service.get("pids_limit",0))>0,"resource bounds")
        image=service.get("image","")
        require(bool(re.fullmatch(r"(?:[^\s]+@)?sha256:[a-f0-9]{64}",image)),"immutable rehearsal image digest or local content ID")
        if name=="mongo": require(bool(re.match(r"(?:(?:docker.io/)?library/)?mongo[:@]",image)),"official Mongo image")
        if name=="caddy": require(bool(re.match(r"(?:(?:docker.io/)?library/)?caddy:2\.11\.9-alpine@",image)),"reviewed Caddy version")
        if name=="mail": require(bool(re.match(r"(?:docker.io/)?axllent/mailpit[:@]",image)),"official Mailpit image")
        if name!="caddy": require(not service.get("ports"),"no application publication")
        for mount in service.get("volumes",[]):
            if mount["type"]=="bind":
                allowed={"caddy":ROOT/"deploy/Caddyfile.rehearsal","prepare":ROOT/"deploy/rehearsal/prepare.py","storage":ROOT/"deploy/rehearsal/storage_mock.py"}
                require(name in allowed and Path(mount["source"]).resolve()==allowed[name] and mount.get("read_only"),"only reviewed fixture mounts")
            else: require(mount["type"]=="volume" and mount["source"] in ("mongo_data","mongo_config","mail_tls"),"rehearsal-owned volumes")
    require(set(model.get("volumes",{}))=={"mongo_data","mongo_config","mail_tls"} and
            all(not v.get("external") and v.get("name")=="landvilla-rehearsal_"+k for k,v in model["volumes"].items()),"unique disposable volumes")
    ports=services["caddy"].get("ports",[])
    require(len(ports)==1 and ports[0].get("host_ip")=="127.0.0.1" and ports[0].get("target")==8443 and str(ports[0].get("published"))=="8443" and ports[0].get("protocol")=="tcp","loopback TLS only")
    api=services["api"]["environment"]
    require(services["api"]["image"]==services["prepare"]["image"]==services["storage"]["image"],"identical tested API artifact")
    require(api.get("DEPLOYMENT_TIER")=="rehearsal" and api.get("APP_ENV")=="production" and api.get("FORWARDED_ALLOW_IPS")==str(peer),"rehearsal identity")
    validate_environment(api)
    require(services["prepare"]["environment"]==api,"same disposable setup target")
    require(all(api.get(k)=="false" for k in ("SEED_ON_STARTUP","SEED_DEMO_LISTINGS","SEED_TEST_SESSIONS","ALLOW_LIVE_PAYMENTS","REFUNDS_ENABLED","GOOGLE_PLAY_BILLING_ENABLED")),"seeds and billing disabled")
    require(api.get("S3_ACCESS_KEY_ID")=="rehearsal-only" and api.get("S3_SECRET_ACCESS_KEY")=="rehearsal-only-never-production" and
            api.get("OTP_HMAC_SECRET")=="rehearsal-only-public-fixture-not-a-production-secret","synthetic credentials only")
    require(api.get("SMTP_HOST")=="mail" and api.get("SMTP_PORT")=="1025" and api.get("SMTP_USERNAME")=="rehearsal" and api.get("SMTP_PASSWORD")=="rehearsal-only" and not api.get("GOOGLE_CLIENT_IDS"),"local synthetic identity providers")
    web=services["web"]["environment"]
    require(web.get("WEB_ORIGIN")=="https://localhost:8443" and web.get("BACKEND_ORIGIN")=="http://api:8000" and web.get("BACKEND_TRANSPORT")=="private-http","fixed rehearsal transport")
    require(web.get("LANDVILLA_INGRESS_TOKEN")=="d"*64 and web.get("WEB_API_IP_KEY")=="e"*64 and api.get("WEB_API_IP_KEY")=="e"*64 and services["caddy"]["environment"].get("LANDVILLA_INGRESS_TOKEN")=="d"*64,"synthetic authenticated ingress")
    require(web.get("CLIENT_IP_MODE")=="signed-v1","authenticated rehearsal identity")
    require(set(services["mail"].get("environment",{}))=={"MP_DATABASE","MP_MAX_MESSAGES","MP_DISABLE_VERSION_CHECK","MP_SMTP_DISABLE_RDNS","MP_QUIET","MP_SMTP_AUTH","MP_SMTP_TLS_CERT","MP_SMTP_TLS_KEY","MP_SMTP_REQUIRE_STARTTLS"},"no mail relay or alternate provider")
    for name in ("web","caddy","storage","mail","mongo"):
        require(not(set(services[name].get("environment",{})) & {"MONGO_URL","S3_ACCESS_KEY_ID","S3_SECRET_ACCESS_KEY","OTP_HMAC_SECRET"}),"API fixture credential scoping")
    return subnet


def host_collisions(subnet):
    def run(command):
        result=subprocess.run(command,capture_output=True,text=True,timeout=30,check=False)
        require(result.returncode==0,"host inventory unavailable")
        return result.stdout
    ids=run(["docker","network","ls","-q"]).split()
    if ids:
        for network in json.loads(run(["docker","network","inspect",*ids])):
            # Docker's built-in host/none networks legitimately return Config: null.
            for config in network.get("IPAM",{}).get("Config") or []:
                existing=ipaddress.ip_network(config.get("Subnet","0.0.0.0/32"))
                require(existing.version!=4 or not subnet.overlaps(existing),"existing Docker subnet collision")
    for route in json.loads(run(["ip","-j","-4","route","show","table","all"])):
        destination=route.get("dst","default")
        if destination=="default": continue
        existing=ipaddress.ip_network(destination,strict=False)
        require(not subnet.overlaps(existing),"host route collision")
    require(not run(["docker","ps","-aq","--filter","label=com.docker.compose.project=landvilla-rehearsal"]).strip(),"existing rehearsal project requires explicit reuse review")
    # Does not prove VPC/VPN/peering remote route absence; approval still required.


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--env-file",required=True)
    p.add_argument("--compose-binary")
    p.add_argument("--host-check",action="store_true")
    args=p.parse_args()
    try:
        subnet=validate(resolve(Path(args.env_file).resolve(),args.compose_binary))
        if args.host_check: host_collisions(subnet)
    except Exception:
        print("BLOCKED rehearsal configuration or collision check; values withheld")
        return 1
    print("PASS rehearsal declarations"+(" and local host collision checks" if args.host_check else " only"))
    print("BLOCKED until approved remote route inventory and Linux acceptance; no directional isolation claim")
    return 0


if __name__=="__main__": raise SystemExit(main())
