#!/bin/sh
# Read-only inspection. No application imports, environment values or broad inspect.
set -eu
printf 'OS/architecture\n'
uname -sm
cat /etc/os-release
printf 'Capacity\n'
df -h / /opt
df -i / /opt
free -m
printf 'Docker versions and existing resources\n'
docker version --format '{{.Server.Version}}'
docker compose version --short
docker ps -a --format '{{.Names}} {{.Image}} {{.Status}} {{.Ports}}'
docker network ls
docker network inspect --format '{{.Name}} {{json .IPAM.Config}} {{.Internal}} {{.EnableIPv6}}' $(docker network ls -q)
docker volume ls
docker image ls --digests --format '{{.Repository}}:{{.Tag}} {{.Digest}} {{.Size}}'
printf 'Routes and listeners\n'
ip -4 route
ip -6 route
ss -lnt
printf 'Checkout identity\n'
git -C /opt/landvilla --no-optional-locks branch --show-current
git -C /opt/landvilla --no-optional-locks rev-parse HEAD
git -C /opt/landvilla --no-optional-locks status --short
printf 'Environment metadata only\n'
sudo -n stat -c '%U %G %a %n' /etc/landvilla/production.env
sudo -n python3 - <<'PY'
from pathlib import Path
names = {line.split('=', 1)[0].strip() for line in Path('/etc/landvilla/production.env').read_text().splitlines()
         if '=' in line and not line.lstrip().startswith('#')}
for name in ('MONGO_URL','DB_NAME','S3_ENDPOINT','S3_BUCKET','S3_ACCESS_KEY_ID','S3_SECRET_ACCESS_KEY','OTP_HMAC_SECRET','IDENTITY_ENABLED'):
    print(name + ': ' + ('PRESENT' if name in names else 'MISSING'))
PY
