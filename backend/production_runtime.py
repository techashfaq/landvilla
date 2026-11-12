"""Production boundaries. No connections or environment-file reads at import time."""
import asyncio
import ipaddress
import json
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qsl, unquote


PRIVATE_PROXY_NETWORKS = tuple(ipaddress.IPv4Network(value) for value in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
))
HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")


def trusted_proxy_addresses(value):
    """Uvicorn 0.25 matches literal peer addresses; it does not interpret CIDRs."""
    addresses = value.split(",")
    for entry in addresses:
        address = entry.strip()
        try:
            parsed = ipaddress.IPv4Address(address)
        except ipaddress.AddressValueError:
            raise RuntimeError("Production requires explicit private IPv4 proxy addresses") from None
        if str(parsed) != address or not any(parsed in network for network in PRIVATE_PROXY_NETWORKS):
            raise RuntimeError("Production requires explicit private IPv4 proxy addresses")
    return [address.strip() for address in addresses]


def valid_hostname(host):
    # Starlette 0.37 splits Host at ':'; IPv6 host literals are not supported here.
    if not host or len(host) > 253 or host != host.lower():
        return False
    if re.fullmatch(r"[0-9.]+", host):
        try:
            return str(ipaddress.IPv4Address(host)) == host
        except ipaddress.AddressValueError:
            return False
    return all(HOST_LABEL.fullmatch(label) for label in host.split("."))


def trusted_hostnames(value):
    hosts = [host.strip() for host in value.split(",")]
    if any(not valid_hostname(host) for host in hosts):
        raise RuntimeError("Production requires explicit canonical hostnames in TRUSTED_HOSTS")
    if "127.0.0.1" not in hosts:
        raise RuntimeError("Production requires 127.0.0.1 in TRUSTED_HOSTS for container probes")
    return hosts


def add_production_host_middleware(application, env):
    """Call last so invalid hosts are rejected before browser guards or DB access."""
    if env.get("APP_ENV", "development").lower() == "production":
        from starlette.middleware.trustedhost import TrustedHostMiddleware
        from starlette.responses import PlainTextResponse

        class StrictTrustedHostMiddleware(TrustedHostMiddleware):
            async def __call__(self, scope, receive, send):
                if scope["type"] in ("http", "websocket"):
                    values = [value for name, value in scope["headers"] if name == b"host"]
                    valid = len(values) == 1
                    if valid:
                        try:
                            authority = values[0].decode("ascii")
                            host, separator, port = authority.partition(":")
                            valid = valid_hostname(host) and (not separator or
                                (bool(re.fullmatch(r"[0-9]{1,5}", port)) and 1 <= int(port) <= 65535))
                        except UnicodeDecodeError:
                            valid = False
                    # Validate allowlist membership here as well: older Starlette
                    # rejects untrusted WebSocket hosts with HTTP response events,
                    # which are invalid without the optional denial extension.
                    if not valid or host not in self.allowed_hosts:
                        if scope["type"] == "websocket":
                            await send({"type": "websocket.close", "code": 1008})
                        else:
                            await PlainTextResponse("Invalid host header", status_code=400)(scope, receive, send)
                        return
                # Old Starlette validates only the text before ':'. Validate the
                # complete authority first so malformed ports cannot poison URL paths.
                await super().__call__(scope, receive, send)

        application.add_middleware(StrictTrustedHostMiddleware,
                                   allowed_hosts=trusted_hostnames(env["TRUSTED_HOSTS"]),
                                   www_redirect=False)


def validate_environment(env):
    if env.get("APP_ENV", "development").lower() != "production":
        return
    required = ("MONGO_URL", "DB_NAME", "CORS_ORIGINS", "WEB_APP_ORIGINS", "TRUSTED_HOSTS",
                "S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "FORWARDED_ALLOW_IPS", "OTP_HMAC_SECRET")
    for name in required:
        if not env.get(name, "").strip():
            raise RuntimeError(f"Production requires {name}")
    tier = env.get("DEPLOYMENT_TIER", "production")
    if tier not in ("production", "rehearsal"):
        raise RuntimeError("Invalid deployment tier")
    rehearsal = tier == "rehearsal"
    database = "landvilla_rehearsal" if rehearsal else "landvilla_prod"
    bucket = "landvilla-property-media-rehearsal" if rehearsal else "landvilla-property-media-prod"
    if env["DB_NAME"] != database or env["S3_BUCKET"] != bucket:
        raise RuntimeError("Database and bucket must match the deployment tier")
    mongo = urlsplit(env["MONGO_URL"])
    options = parse_qsl(mongo.query, keep_blank_values=True)
    normalized = {key.lower(): value.lower() for key, value in options}
    if (";" in mongo.query or len(normalized) != len(options) or mongo.fragment or
            mongo.scheme not in ("mongodb", "mongodb+srv") or not mongo.hostname or
            unquote(mongo.path) not in ("", "/", "/" + database)):
        raise RuntimeError("Invalid MongoDB connection configuration")
    if rehearsal:
        if env["MONGO_URL"] != "mongodb://mongo:27017/landvilla_rehearsal?replicaSet=lv_rehearsal":
            raise RuntimeError("Rehearsal requires the exact disposable MongoDB service")
        if env["S3_ENDPOINT"] != "http://storage:9000":
            raise RuntimeError("Rehearsal requires the exact disposable storage service")
        if env["WEB_APP_ORIGINS"] != "https://localhost:8443" or env["CORS_ORIGINS"] != "https://localhost:8443":
            raise RuntimeError("Rehearsal requires the loopback TLS origin")
    elif (any(normalized.get(key) not in (None, "false") for key in
              ("tlsinsecure", "tlsallowinvalidcertificates", "tlsallowinvalidhostnames", "tlsdisablecertificaterevocationcheck", "tlsdisableocspendpointcheck")) or
          normalized.get("tls") == "false" or normalized.get("ssl") == "false" or
          (mongo.scheme == "mongodb" and normalized.get("tls") != "true") or
          ("tls" in normalized and "ssl" in normalized)):
        raise RuntimeError("Production MongoDB requires verified TLS")
    if env.get("CLIENT_IP_MODE") != "signed-v1" or not re.fullmatch(r"[a-f0-9]{64}", env.get("WEB_API_IP_KEY", "")):
        raise RuntimeError("Authenticated ingress identity configuration required")
    if not rehearsal and env["WEB_API_IP_KEY"] == "e" * 64:
        raise RuntimeError("Production cannot reuse the public rehearsal identity key")
    for name in ("SEED_ON_STARTUP", "SEED_DEMO_LISTINGS", "SEED_TEST_SESSIONS"):
        if env.get(name, "false").lower() != "false":
            raise RuntimeError(f"Production requires {name}=false")
    if env.get("STORAGE_PROVIDER") != "cloudflare_r2":
        raise RuntimeError("Production requires STORAGE_PROVIDER=cloudflare_r2")
    if env.get("IDENTITY_ENABLED", "false").lower() != "true" or len(env["OTP_HMAC_SECRET"]) < 32:
        raise RuntimeError("Production requires identity and a strong OTP_HMAC_SECRET")
    trusted_proxy_addresses(env["FORWARDED_ALLOW_IPS"])
    for name in ("CORS_ORIGINS", "WEB_APP_ORIGINS", "S3_ENDPOINT"):
        if rehearsal and name == "S3_ENDPOINT":
            continue  # Exact disposable endpoint checked above; never allowed in production.
        for value in env[name].split(","):
            try:
                parsed = urlsplit(value.strip())
                port = parsed.port
            except ValueError:
                raise RuntimeError(f"Invalid production origin in {name}") from None
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                    or not valid_hostname(parsed.hostname) or port == 0
                    or parsed.query or parsed.fragment or parsed.path not in ("", "/") or "*" in value
                    or (name != "S3_ENDPOINT" and parsed.path)):
                raise RuntimeError(f"Production requires safe HTTPS origins in {name}")
    trusted_hostnames(env["TRUSTED_HOSTS"])


class SafeJSONFormatter(logging.Formatter):
    """Never serialize arbitrary messages, exception text, query strings or headers."""
    def format(self, record):
        payload = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": record.levelname}
        for key in ("event", "request_id", "status", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        payload.setdefault("event", "application_log")
        return json.dumps(payload)


async def dependency_readiness(database, storage_client=None, bucket=None):
    """Read-only probes; topology eligibility is not proof of transaction privileges."""
    await database.command("ping")
    topology = await database.command("hello")
    if not (topology.get("setName") or topology.get("msg") == "isdbgrid") or topology.get("logicalSessionTimeoutMinutes") is None:
        raise RuntimeError("Transaction-capable MongoDB topology required")
    if storage_client is not None:
        await asyncio.to_thread(storage_client.head_bucket, Bucket=bucket)


def readiness_storage_client(env):
    # Separate short-lived probe limits; do not change upload/download timeouts.
    import boto3
    from botocore.config import Config
    return boto3.client("s3", endpoint_url=env["S3_ENDPOINT"],
                        aws_access_key_id=env["S3_ACCESS_KEY_ID"], aws_secret_access_key=env["S3_SECRET_ACCESS_KEY"],
                        region_name=env.get("S3_REGION", "auto"),
                        config=Config(signature_version="s3v4", connect_timeout=1, read_timeout=1, retries={"total_max_attempts": 1}))
