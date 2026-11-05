"""Cookie transport for the existing session store. No browser bearer fallback."""
import hashlib
import logging
import time
import hmac
import os
import secrets
from datetime import timedelta
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from server import db, now, aware, public_user

router = APIRouter(prefix="/api/auth/browser")
perf_logger = logging.getLogger("landvilla.auth.perf")
async def timed_auth(label, operation):
    started = time.perf_counter()
    try:
        return await operation
    finally:
        perf_logger.info(
            "auth_perf stage=%s duration_ms=%.1f",
            label,
            (time.perf_counter() - started) * 1000,
        )
SECURE_COOKIE = "__Host-lv_session"
DEV_COOKIE = "lv_dev_session"


def digest(value):
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def origins():
    production = os.getenv("APP_ENV", "development").lower() == "production"
    values = [v.strip() for v in os.getenv("WEB_APP_ORIGINS", "" if production else "http://localhost:8081,http://localhost:19006").split(",") if v.strip()]
    for value in values:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username or (production and parsed.scheme != "https"):
            raise HTTPException(503, "Browser origins are not configured safely")
    if not values:
        raise HTTPException(503, "Browser origins are not configured")
    return values


def browser_request(request):
    return bool(request.headers.get("origin") or request.headers.get("sec-fetch-mode") or
                request.headers.get("x-lv-client") == "web" or
                SECURE_COOKIE in request.cookies or DEV_COOKIE in request.cookies)


def cookie_settings(request):
    secure = request.url.scheme == "https" or os.getenv("APP_ENV", "development").lower() == "production"
    if not secure and request.url.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise HTTPException(503, "Browser sessions require HTTPS except on local loopback")
    return (SECURE_COOKIE if secure else DEV_COOKIE), secure


def check_origin(request, safe=False):
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Browser sessions require the web app and API on the same site")
    origin = request.headers.get("origin")
    if not origin and safe:
        ref = urlsplit(request.headers.get("referer", ""))
        origin = f"{ref.scheme}://{ref.netloc}" if ref.netloc else None
    if origin not in origins():
        raise HTTPException(403, "Untrusted browser origin")


async def session(request):
    name, _ = cookie_settings(request)
    token = request.cookies.get(name, "")
    if not token:
        return None
    return await timed_auth(
    "browser_session_lookup",
    db.user_sessions.find_one({"session_token": digest(token), "transport": "browser",
        "expires_at": {"$gt": now()}, "consumed": {"$ne": True}})
)


async def user_from_session(row):
    if not row or not row.get("user_id"):
        return None
    user = await db.users.find_one({"user_id": row["user_id"]}, {"_id": 0})
    if not user or user.get("suspended") or user.get("account_status", "active") != "active":
        return None
    user["_session_created_at"] = aware(row.get("created_at"))
    return user


async def guard(request):
    if not request.url.path.startswith("/api/") or request.method == "OPTIONS":
        return
    # Server-to-server callbacks retain raw-body signature verification.
    if request.url.path == "/api/payments/razorpay/webhook":
        return
    web = browser_request(request)
    request.state.browser = web
    if not web:
        return
    if request.headers.get("authorization"):
        raise HTTPException(403, "Browser bearer authentication is disabled. Sign in again")
    # No session-id supplied by a browser is ever exchanged with the managed provider.
    if request.url.path == "/api/auth/session":
        raise HTTPException(503, "Managed web sign-in is unavailable until callback state verification is configured. Use email or independent Google")
    if request.method in ("GET", "HEAD"):
        if request.headers.get("origin"):
            check_origin(request)
        # A stale tab must not silently fetch another account's private data.
        if request.headers.get("x-csrf-token") and request.url.path != "/api/auth/browser/bootstrap":
            row = await session(request)
            if not row or not hmac.compare_digest(row["csrf"], request.headers["x-csrf-token"]):
                raise HTTPException(401, "Browser session changed. Reload and sign in again")
        return
    check_origin(request)
    row = await session(request)
    supplied = request.headers.get("x-csrf-token", "")
    if not row and request.url.path == "/api/auth/logout":
        # There is no live session to revoke; trusted-origin logout can expire an obsolete cookie.
        request.state.browser_session = None
        return
    if not row or not supplied or not hmac.compare_digest(row["csrf"], supplied):
        raise HTTPException(403, "Browser session changed or CSRF token is invalid. Reload and try again")
    request.state.browser_session = row


def respond(request, token, row, user):
    name, secure = cookie_settings(request)
    response = JSONResponse({"user": public_user(user) if user else None, "csrf_token": row["csrf"],
                             "expires_in": max(0, int((aware(row["expires_at"]) - now()).total_seconds()))})
    response.set_cookie(name, token, max_age=max(0, int((aware(row["expires_at"]) - now()).total_seconds())),
                        secure=secure, httponly=True, samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"
    return response


async def create(request, user=None):
    cookie_settings(request)
    token = secrets.token_urlsafe(48)
    row = {"session_token": digest(token), "transport": "browser", "user_id": user["user_id"] if user else None,
           "csrf": secrets.token_urlsafe(32), "created_at": now(),
           "expires_at": now() + (timedelta(days=7) if user else timedelta(minutes=15))}
    await timed_auth("browser_session_insert", db.user_sessions.insert_one(row))
    return respond(request, token, row, user)


@router.get("/bootstrap")
async def bootstrap(request: Request):
    check_origin(request, safe=True)
    from identity import require_identity, throttle
    await require_identity()
    row = await session(request)
    user = await user_from_session(row)
    if row and (not row.get("user_id") or user):
        return {"user": public_user(user) if user else None, "csrf_token": row["csrf"],
                "expires_in": max(0, int((aware(row["expires_at"]) - now()).total_seconds()))}
    await throttle("browser-bootstrap:" + (request.client.host if request.client else "unknown"), 30, 3600)
    return await create(request)


async def issue(request, user):
    row = getattr(request.state, "browser_session", None)
    if not row:
        raise HTTPException(403, "Initialize a browser session before signing in")
    result = await timed_auth(
    "browser_session_consume",
    db.user_sessions.update_one({"_id": row["_id"], "consumed": {"$ne": True},
        "expires_at": {"$gt": now()}}, {"$set": {"consumed": True}})
)
    if not result.modified_count:
        raise HTTPException(409, "Browser session already changed. Reload and try again")
    return await create(request, user)


async def logout(request):
    row = getattr(request.state, "browser_session", None)
    if row:
        await db.user_sessions.delete_one({"_id": row["_id"]})
    name, secure = cookie_settings(request)
    response = JSONResponse({"ok": True})
    response.delete_cookie(name, path="/", secure=secure, httponly=True, samesite="lax")
    return response


@router.post("/google-nonce")
async def google_nonce(request: Request):
    row = request.state.browser_session
    nonce = secrets.token_urlsafe(32)
    await db.user_sessions.update_one({"_id": row["_id"]}, {"$set": {
        "google_nonce": digest(nonce), "nonce_expires_at": now() + timedelta(minutes=5)}})
    return {"nonce": nonce}


async def claim_google(request, info):
    if not getattr(request.state, "browser", False):
        return
    row = request.state.browser_session
    nonce = info.get("nonce")
    if not isinstance(nonce, str) or not nonce:
        raise HTTPException(400, "Google callback does not belong to this browser")
    result = await db.user_sessions.update_one({"_id": row["_id"], "google_nonce": digest(nonce),
        "nonce_expires_at": {"$gt": now()}, "consumed": {"$ne": True}}, {"$unset": {"google_nonce": "", "nonce_expires_at": ""}})
    if not result.modified_count:
        raise HTTPException(400, "Google callback expired or was already used")
