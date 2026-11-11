"""Production boundaries. No connections or environment-file reads at import time."""
import asyncio
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlsplit


def validate_environment(env):
    if env.get("APP_ENV", "development").lower() != "production":
        return
    required = ("MONGO_URL", "DB_NAME", "CORS_ORIGINS", "WEB_APP_ORIGINS", "TRUSTED_HOSTS",
                "S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "FORWARDED_ALLOW_IPS", "OTP_HMAC_SECRET")
    for name in required:
        if not env.get(name, "").strip():
            raise RuntimeError(f"Production requires {name}")
    for name in ("SEED_ON_STARTUP", "SEED_DEMO_LISTINGS", "SEED_TEST_SESSIONS"):
        if env.get(name, "false").lower() != "false":
            raise RuntimeError(f"Production requires {name}=false")
    if env.get("STORAGE_PROVIDER") != "cloudflare_r2":
        raise RuntimeError("Production requires STORAGE_PROVIDER=cloudflare_r2")
    if env.get("IDENTITY_ENABLED", "false").lower() != "true" or len(env["OTP_HMAC_SECRET"]) < 32:
        raise RuntimeError("Production requires identity and a strong OTP_HMAC_SECRET")
    if "*" in env["FORWARDED_ALLOW_IPS"]:
        raise RuntimeError("Production requires explicit proxy addresses")
    for name in ("CORS_ORIGINS", "WEB_APP_ORIGINS", "S3_ENDPOINT"):
        for value in env[name].split(","):
            try:
                parsed = urlsplit(value.strip())
            except ValueError:
                raise RuntimeError(f"Invalid production origin in {name}") from None
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                    or parsed.query or parsed.fragment or parsed.path not in ("", "/") or "*" in value):
                raise RuntimeError(f"Production requires safe HTTPS origins in {name}")
    if any(not h.strip() or "*" in h or "/" in h or ":" in h for h in env["TRUSTED_HOSTS"].split(",")):
        raise RuntimeError("Production requires explicit hostnames in TRUSTED_HOSTS")


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
