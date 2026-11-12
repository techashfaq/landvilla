"""Authenticated rate-limit identity; never changes URL, Host, scheme or session scope."""
import hashlib
import hmac
import ipaddress
import os
import re
import time
from fastapi import HTTPException


def rate_identity(request):
    peer = request.client.host if request.client else "unknown"
    if os.getenv("APP_ENV", "development").lower() != "production":
        return peer
    if os.getenv("CLIENT_IP_MODE") != "signed-v1":
        raise HTTPException(503, "Ingress identity unavailable")
    # Uvicorn must receive no X-Forwarded-For. Keep the real Web peer for this check.
    if request.headers.get("x-forwarded-for") or peer not in os.getenv("FORWARDED_ALLOW_IPS", "").split(","):
        raise HTTPException(400, "Invalid ingress identity")
    fields = ("x-lv-client-ip", "x-lv-ip-time", "x-lv-ip-signature")
    if any(len(request.headers.getlist(name)) != 1 for name in fields):
        raise HTTPException(400, "Invalid ingress identity")
    address, stamp, signature = (request.headers[name] for name in fields)
    try:
        if "%" in address or not re.fullmatch(r"[0-9]{10}", stamp) or abs(time.time() - int(stamp)) > 60:
            raise ValueError()
        parsed = ipaddress.ip_address(address)
        key = os.environ["WEB_API_IP_KEY"]
        if not re.fullmatch(r"[a-f0-9]{64}", key) or not re.fullmatch(r"[a-f0-9]{64}", signature):
            raise ValueError()
        message = "\n".join(("v1", stamp, request.method, request.url.path, address))
        expected = hmac.new(bytes.fromhex(key), message.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError()
        if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped:
            parsed = parsed.ipv4_mapped
        return str(parsed)
    except (ValueError, KeyError):
        raise HTTPException(400, "Invalid ingress identity") from None
