"""Read-only assignment presence audit. Fixed variable names/statuses only; never values.

No dotenv interpolation, shell evaluation, application import or provider connection.
Presence is not validation of identities, credentials, TLS, or provider permissions.
"""
import argparse
from pathlib import Path
import re

API_REQUIRED=("MONGO_URL","DB_NAME","STORAGE_PROVIDER","IDENTITY_ENABLED","OTP_HMAC_SECRET",
              "S3_ENDPOINT","S3_BUCKET","S3_ACCESS_KEY_ID","S3_SECRET_ACCESS_KEY")
API_CONDITIONAL=("SMTP_HOST","SMTP_FROM","SMTP_USERNAME","SMTP_PASSWORD","SMTP_PORT",
                 "TWILIO_ACCOUNT_SID","TWILIO_AUTH_TOKEN","TWILIO_FROM","GOOGLE_CLIENT_IDS")
API_OPTIONAL=("S3_REGION","ADMIN_EMAILS")
COMPOSE_REQUIRED=("LANDVILLA_ENV_FILE","LANDVILLA_DOCKER_SUBNET","LANDVILLA_DOCKER_DYNAMIC_RANGE",
                  "LANDVILLA_WEB_PROXY_IP","LANDVILLA_API_IMAGE","LANDVILLA_WEB_IMAGE","LANDVILLA_CADDY_IMAGE",
                  "LANDVILLA_ACME_EMAIL","LANDVILLA_INGRESS_TOKEN","LANDVILLA_WEB_API_IP_KEY")


def assignment_status(content,names):
    counts={name:[] for name in names}
    for line in content.splitlines():
        match=re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$",line)
        if match and match[1] in counts:
            value=match[2].strip()
            counts[match[1]].append(value not in ("", "''", '""') and not value.startswith("#"))
    return {name:("MISSING" if not entries else "DUPLICATE" if len(entries)>1 else
                  "PRESENT" if entries[0] else "EMPTY") for name,entries in counts.items()}


def inspect(path,required,conditional=(),optional=()):
    names=required+conditional+optional
    try: statuses=assignment_status(path.read_text(encoding="utf-8"),names)
    except (OSError,UnicodeError):
        print("NOT VERIFIED: file unavailable or unreadable; path/details withheld")
        return False
    for group,items in (("required",required),("conditional",conditional),("optional",optional)):
        for name in items: print(group+" "+name+": "+statuses[name])
    return all(statuses[name]=="PRESENT" for name in required)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--api-env",type=Path,default=Path("/etc/landvilla/production.env"))
    p.add_argument("--compose-env",type=Path,default=Path("/etc/landvilla/compose.env"))
    args=p.parse_args()
    print("API file assignment audit")
    api=inspect(args.api_env,API_REQUIRED,API_CONDITIONAL,API_OPTIONAL)
    print("Compose file assignment audit")
    compose=inspect(args.compose_env,COMPOSE_REQUIRED,optional=("NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID",))
    print("Presence only; values, interpolation, identities and runtime NOT VERIFIED")
    return 0 if api and compose else 1


if __name__=="__main__": raise SystemExit(main())
