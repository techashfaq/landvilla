from client_identity import rate_identity
"""Passwordless identities. No test OTP, no plaintext OTP/session storage."""
import hashlib
import logging
import time
import hmac
import os
import re
import secrets
import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from server import db, current_user, now, aware, public_user, clean
import browser_sessions

router = APIRouter(prefix="/api")

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


def email_value(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise ValueError("Enter a valid email")
    return value


def mobile_value(value: str) -> str:
    value = value.strip().replace(" ", "").replace("-", "")
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
        raise ValueError("Use a mobile number with country code, for example +91 followed by 10 digits")
    return value


class Registration(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: str
    mobile: str
    account_role: Literal["buyer", "owner", "broker", "builder"]
    accept_terms: Literal[True]
    accept_privacy: Literal[True]
    _email = field_validator("email")(email_value)
    _mobile = field_validator("mobile")(mobile_value)


class OtpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identifier: str = Field(max_length=254)
    purpose: Literal["register", "login", "contact"] = "login"
    registration: Optional[Registration] = None


class OtpVerify(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: str = Field(min_length=20, max_length=100)
    code: str = Field(pattern=r"^\d{6}$")


def otp_secret() -> bytes:
    key = os.getenv("OTP_HMAC_SECRET", "")
    if len(key) < 32:
        raise HTTPException(503, "OTP authentication is not configured")
    return key.encode()


def verifier(challenge: str, code: str) -> str:
    return hmac.new(otp_secret(), f"{challenge}:{code}".encode(), hashlib.sha256).hexdigest()


def provider_ready(channel: str):
    required = ["SMTP_HOST", "SMTP_FROM", "SMTP_USERNAME", "SMTP_PASSWORD"] if channel == "email" else ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM"]
    if not all(os.getenv(k, "").strip() for k in required):
        raise HTTPException(503, f"{channel.title()} verification is not configured")
    if channel == "email":
        try:
            port = int(os.getenv("SMTP_PORT", "587"))
            email_value(os.environ["SMTP_FROM"])
            if not 1 <= port <= 65535 or port == 465 or any(c.isspace() for c in os.environ["SMTP_HOST"]):
                raise ValueError()
        except ValueError:
            raise HTTPException(503, "Email verification configuration is invalid") from None
    else:
        if not re.fullmatch(r"AC[0-9a-fA-F]{32}", os.environ["TWILIO_ACCOUNT_SID"]):
            raise HTTPException(503, "SMS verification configuration is invalid")
        sender = os.environ["TWILIO_FROM"]
        if not (re.fullmatch(r"\+[1-9][0-9]{7,14}", sender) or
                (re.fullmatch(r"[A-Za-z0-9 ]{1,11}", sender) and re.search(r"[A-Za-z]", sender))):
            raise HTTPException(503, "SMS verification sender is invalid")


async def require_identity():
    if os.getenv("IDENTITY_ENABLED", "false").lower() != "true":
        raise HTTPException(503, "Passwordless authentication is not enabled")
    if not await db.schema_migrations.find_one({"version": "002_identity_indexes"}):
        raise HTTPException(503, "Authentication indexes must be provisioned before enabling sign-in")
    if await missing_identity_indexes(db):
        raise HTTPException(503, "Authentication indexes are missing or incompatible")


async def missing_identity_indexes(database):
    """Read actual constraints; a migration marker alone is not a security boundary."""
    missing = []
    for collection, field, options in [
        ("users", "email", {"unique": True}),
        ("users", "user_id", {"unique": True}),
        ("users", "mobile", {"unique": True, "partialFilterExpression": {"mobile": {"$type": "string"}}}),
        ("users", "google_sub", {"unique": True, "partialFilterExpression": {"google_sub": {"$type": "string"}}}),
        ("user_sessions", "session_token", {"unique": True}),
        ("user_sessions", "expires_at", {"expireAfterSeconds": 0}),
        ("otp_challenges", "challenge_id", {"unique": True}),
        ("otp_challenges", "expires_at", {"expireAfterSeconds": 0}),
        ("auth_limits", "expires_at", {"expireAfterSeconds": 0}),
    ]:
        indexes = await database[collection].index_information()
        if not any(list(index.get("key", [])) == [(field, 1)]
                   and all(index.get(k) == v for k, v in options.items())
                   and not index.get("sparse")
                   and ("partialFilterExpression" in options or not index.get("partialFilterExpression"))
                   for index in indexes.values()):
            missing.append(f"{collection}.{field}")
    return missing


def require_recent_auth(user):
    created = user.get("_session_created_at")
    if not created or now() - aware(created) > timedelta(minutes=15):
        raise HTTPException(403, "Sign in again before changing contact information")


def smtp_send(identifier: str, code: str):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = os.environ["SMTP_FROM"], identifier, "LANDVILLA verification code"
    msg.set_content(f"Your LANDVILLA code is {code}. It expires in five minutes. Do not share this code.")
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")), timeout=15) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)


async def deliver(channel: str, identifier: str, code: str):
    try:
        if channel == "email":
            await run_in_threadpool(smtp_send, identifier, code)
        else:
            sid = os.environ["TWILIO_ACCOUNT_SID"]
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                    auth=(sid, os.environ["TWILIO_AUTH_TOKEN"]), data={"From": os.environ["TWILIO_FROM"], "To": identifier,
                    "Body": f"Your LANDVILLA code is {code}. Valid for five minutes. Do not share it."})
                response.raise_for_status()
    except Exception:
        raise HTTPException(503, "Verification delivery is unavailable. Please try again later") from None


async def throttle(subject: str, limit: int, seconds: int):
    # Unique Mongo _id provides an atomic fixed-window counter across API workers.
    bucket = int(now().timestamp()) // seconds
    key = hashlib.sha256(f"{subject}:{bucket}".encode()).hexdigest()
    try:
        row = await db.auth_limits.find_one_and_update({"_id": key},
            {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": now() + timedelta(seconds=seconds * 2)}},
            upsert=True, return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        row = await db.auth_limits.find_one_and_update({"_id": key}, {"$inc": {"count": 1}}, return_document=ReturnDocument.AFTER)
        if row is None:
            raise HTTPException(503, "Authentication temporarily unavailable") from None
    if row["count"] > limit:
        raise HTTPException(429, "Too many attempts. Please try later", headers={"Retry-After": str(seconds)})


@router.post("/auth/otp/request")
async def request_otp(body: OtpRequest, request: Request):
    otp_secret()
    await timed_auth("otp_request_identity_preflight", require_identity())
    try:
        channel = "email" if "@" in body.identifier else "mobile"
        identifier = email_value(body.identifier) if channel == "email" else mobile_value(body.identifier)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    provider_ready(channel)
    await throttle("ip:" + rate_identity(request), 20, 3600)
    await throttle("identifier:" + identifier, 5, 3600)
    user = None
    if body.purpose == "contact":
        user = await current_user(request)
        require_recent_auth(user)
        await throttle("account:" + user["user_id"], 5, 3600)
    if body.purpose == "register" and (not body.registration or channel != "email" or body.registration.email != identifier):
        raise HTTPException(422, "Registration requires matching email and complete profile")
    key = hashlib.sha256(f"{body.purpose}:{identifier}:{user['user_id'] if user else ''}".encode()).hexdigest()
    challenge = secrets.token_urlsafe(32)
    code = f"{secrets.randbelow(1_000_000):06d}"
    row = {"challenge_id": challenge, "identifier": identifier, "channel": channel, "purpose": body.purpose,
           "verifier": verifier(challenge, code), "attempts": 0, "used": False, "delivered": False, "expires_at": now() + timedelta(minutes=5),
           "resend_at": now() + timedelta(seconds=60), "user_id": user["user_id"] if user else None,
           "registration": body.registration.model_dump() if body.registration else None}
    if body.purpose == "contact" and channel == "mobile":
        # Snapshot plus version rejects stale and changed-away-then-back challenges.
        row["mobile_state"] = {
            field: user[field] if field in user else {"$exists": False}
            for field in ("mobile", "mobile_verified", "mobile_contact_version")
        }
    browser = getattr(request.state, "browser_session", None)
    row["browser_session"] = browser["session_token"] if browser else None
    try:
        await db.otp_challenges.update_one({"_id": key, "$or": [{"resend_at": {"$lte": now()}}, {"resend_at": {"$exists": False}}]},
                                           {"$set": row}, upsert=True)
    except DuplicateKeyError:
        raise HTTPException(429, "Please wait before requesting another code", headers={"Retry-After": "60"}) from None
    existing = await db.users.find_one({channel: identifier})
    eligible = (body.purpose == "register" and existing is None) or (body.purpose == "login" and existing and existing.get(channel + "_verified")) or body.purpose == "contact"
    if eligible:
        try:
            if body.purpose == "login":
                await db.otp_challenges.update_one({"_id": key, "challenge_id": challenge},
                    {"$set": {"user_id": existing["user_id"]}})
            await deliver(channel, identifier, code)
            await db.otp_challenges.update_one({"_id": key, "challenge_id": challenge, "used": False}, {"$set": {"delivered": True}})
        except HTTPException:
            await db.otp_challenges.update_one({"_id": key, "challenge_id": challenge}, {"$set": {"used": True}})
            raise
    return {"challenge_id": challenge, "expires_in": 300, "resend_after": 60,
            "message": "If eligible, a verification code has been sent"}


async def issue_session(user: dict, request: Request = None):
    if user.get("suspended") or user.get("account_status", "active") != "active":
        raise HTTPException(403, "Account unavailable")
    if request and getattr(request.state, "browser", False):
        return await browser_sessions.issue(request, user)
    token = secrets.token_urlsafe(48)
    await db.user_sessions.insert_one({"session_token": "sha256:" + hashlib.sha256(token.encode()).hexdigest(),
        "user_id": user["user_id"], "transport": "native", "created_at": now(), "expires_at": now() + timedelta(days=7)})
    return {"session_token": token, "user": public_user(user), "expires_in": 604800}


@router.post("/auth/otp/verify")
async def verify_otp(body: OtpVerify, request: Request):
    await timed_auth("identity_preflight", require_identity())
    otp_secret()
    await timed_auth("verify_throttle", throttle("verify-ip:" + rate_identity(request), 50, 3600))
    row = await timed_auth("otp_challenge_lookup", db.otp_challenges.find_one_and_update({"challenge_id": body.challenge_id, "used": False, "delivered": True,
        "expires_at": {"$gt": now()}, "attempts": {"$lt": 5}}, {"$inc": {"attempts": 1}}, return_document=ReturnDocument.AFTER))
    if not row or not hmac.compare_digest(row["verifier"], verifier(body.challenge_id, body.code)):
        raise HTTPException(400, "Invalid or expired verification code")
    browser = getattr(request.state, "browser_session", None)
    if row.get("browser_session") != (browser["session_token"] if browser else None):
        raise HTTPException(400, "Verification belongs to a different sign-in session")
    if row["purpose"] == "contact":
        user = await current_user(request)
        if user["user_id"] != row["user_id"]:
            raise HTTPException(403, "Verification belongs to another account")
        require_recent_auth(user)
    claimed = await timed_auth("otp_mark_used", db.otp_challenges.update_one({"_id": row["_id"], "challenge_id": body.challenge_id, "used": False,
        "delivered": True, "expires_at": {"$gt": now()}}, {"$set": {"used": True}}))
    if not claimed.modified_count:
        raise HTTPException(400, "Invalid or expired verification code")
    channel, identifier = row["channel"], row["identifier"]
    user = await timed_auth("user_lookup", db.users.find_one({channel: identifier}))
    if row["purpose"] == "register":
        if user:
            raise HTTPException(400, "Unable to complete verification. Try signing in")
        profile = {k: v for k, v in row["registration"].items() if k != "mobile"}
        user = {**profile, "user_id": "user_" + secrets.token_hex(12), "role": "buyer", "name": profile["first_name"] + " " + profile["last_name"],
                "email_verified": True, "mobile_verified": False, "account_status": "active", "created_at": now(),
                "terms_accepted_at": now(), "privacy_accepted_at": now()}
        try:
            await db.users.insert_one(user)
        except DuplicateKeyError:
            raise HTTPException(409, "Unable to create account. Try signing in") from None
    elif row["purpose"] == "contact":
        if user and user["user_id"] != row["user_id"]:
            raise HTTPException(409, "Contact cannot be linked")
        match = {"user_id": row["user_id"]}
        changes = {channel: identifier, channel + "_verified": True, "updated_at": now()}
        if channel == "mobile":
            state = row.get("mobile_state")
            if not isinstance(state, dict) or set(state) != {"mobile", "mobile_verified", "mobile_contact_version"}:
                raise HTTPException(409, "Contact verification changed. Request a new code")
            match.update(state)
            changes["mobile_contact_version"] = secrets.token_hex(16)
        try:
            result = await db.users.update_one(match, {"$set": changes})
        except DuplicateKeyError:
            raise HTTPException(409, "Contact cannot be linked") from None
        if not result.matched_count:
            raise HTTPException(409, "Contact verification changed. Request a new code")
        return {"verified": True}
    elif not user or user["user_id"] != row.get("user_id") or not user.get(channel + "_verified"):
        raise HTTPException(400, "Invalid or expired verification code")
    return await timed_auth("issue_session_total", issue_session(user, request))




class ProfileEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    preferred_location: str = Field(default="", max_length=120)


@router.get("/me/profile")
async def get_profile(user: dict = Depends(current_user)):
    fields = ("user_id", "first_name", "last_name", "name", "email", "email_verified", "mobile", "mobile_verified", "role", "account_role", "picture", "created_at", "account_status", "preferred_location")
    profile = clean({k: user.get(k) for k in fields})
    profile["profile_complete"] = all(user.get(k) for k in ("first_name", "last_name", "email_verified", "mobile_verified"))
    return profile


@router.patch("/me/profile")
async def edit_profile(body: ProfileEdit, user: dict = Depends(current_user)):
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {**body.model_dump(), "name": body.first_name + " " + body.last_name, "updated_at": now()}})
    return await get_profile(await db.users.find_one({"user_id": user["user_id"]}))


class GoogleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_token: str = Field(min_length=20, max_length=10000)



def verify_google(token: str):
    audiences = [
        s.strip()
        for s in os.getenv("GOOGLE_CLIENT_IDS", "").split(",")
        if s.strip()
    ]

    if not audiences:
        raise HTTPException(
            503,
            "Independent Google sign-in is not configured"
        )

    try:
        from google.oauth2 import id_token
        from google.auth.transport.requests import Request as GoogleRequest
        from google.auth.exceptions import TransportError
    except ImportError:
        raise HTTPException(
            503,
            "Google verification dependency is unavailable"
        ) from None

    try:
        info = id_token.verify_oauth2_token(
            token,
            GoogleRequest(),
            audience=audiences
        )

        if (
            info.get("email_verified") is not True
            or not isinstance(info.get("sub"), str)
            or not info["sub"]
        ):
            raise ValueError("Google identity verification failed")

        info["email"] = email_value(info.get("email", ""))
        return info

    except TransportError:
        logging.getLogger("landvilla.auth").warning("google_verifier_unavailable")
        raise HTTPException(
            503,
            "Google verification service is unavailable. Please try again later"
        ) from None

    except Exception:
        logging.getLogger("landvilla.auth").warning("google_credential_invalid")
        raise HTTPException(
            401,
            "Invalid Google credential"
        ) from None


@router.post("/auth/google")
async def google_session(body: GoogleIn, request: Request):
    await require_identity()
    await throttle("google:" + rate_identity(request), 30, 3600)
    info = await run_in_threadpool(verify_google, body.id_token)
    await browser_sessions.claim_google(request, info)
    user = await db.users.find_one({"google_sub": info["sub"]})
    if not user:
        email = email_value(info["email"])
        user = await db.users.find_one({"email": email})
        if user:
            raise HTTPException(409, "Sign in using your existing method. Google account linking requires authenticated verification")
        # Third-party Google emails are not proof of current mailbox ownership.
        if not (email.endswith("@gmail.com") or info.get("hd")):
            raise HTTPException(409, "Sign in with email verification to link this account")
        if user and user.get("google_sub") and user["google_sub"] != info["sub"]:
            raise HTTPException(409, "Account linking requires verification")
        if not user:
            user = {"user_id": "user_" + secrets.token_hex(12), "email": email, "role": "buyer", "account_role": "buyer",
                    "created_at": now(), "account_status": "active"}
        user.update({"google_sub": info["sub"], "email_verified": True, "name": info.get("name", ""),
                     "first_name": info.get("given_name", ""), "last_name": info.get("family_name", ""), "picture": info.get("picture")})
        try:
            await db.users.update_one({"user_id": user["user_id"]}, {"$set": {k: v for k, v in user.items() if k != "_id"}}, upsert=True)
        except DuplicateKeyError:
            raise HTTPException(409, "Account linking requires verification") from None
    return await issue_session(user, request)


@router.post("/auth/google/link")
async def link_google(body: GoogleIn, request: Request, user: dict = Depends(current_user)):
    await require_identity()
    require_recent_auth(user)
    await throttle("google-link:" + user["user_id"], 5, 3600)
    try:
        info = await run_in_threadpool(verify_google, body.id_token)
    except HTTPException as exc:
        if exc.status_code == 401:
            # A rejected linking credential does not revoke the valid bearer session.
            raise HTTPException(400, "Invalid Google credential") from None
        raise
    await browser_sessions.claim_google(request, info)
    if not user.get("email_verified") or email_value(user.get("email", "")) != info["email"]:
        raise HTTPException(409, "Verify this Google email on your account before linking")
    try:
        result = await db.users.update_one({"user_id": user["user_id"], "email": info["email"],
            "email_verified": True, "$or": [{"google_sub": {"$exists": False}}, {"google_sub": info["sub"]}]},
            {"$set": {"google_sub": info["sub"], "updated_at": now()}})
    except DuplicateKeyError:
        raise HTTPException(409, "Google identity is already linked") from None
    if not result.matched_count:
        raise HTTPException(409, "Account linking requires verification")
    return {"linked": True}
