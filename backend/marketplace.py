"""LANDVILLA marketplace features: uploads, owner/broker listings, moderation,
broker verification, lead inbox (privacy-safe), featured listing payments (Razorpay).

All permission and privacy rules are enforced here on the server.
Imported at the bottom of server.py (after db/auth helpers exist).
"""
import hashlib
import hmac
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional

import httpx
import requests
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from server import admin_user, aware, clean, current_user, current_user_optional, db, enrich, logger, now

router = APIRouter(prefix="/api")

APP_NAME = "landvilla"
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
RZP_API = "https://api.razorpay.com/v1"
DECLARATION_VERSION = "owner-authority-v1"
MODERATION_DISCLAIMER = ("Listing moderation by LANDVILLA is not a guarantee of title, ownership, approvals or legal status. "
                         "Buyers must do their own legal due diligence.")

_storage_key: Optional[str] = None


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ------------------------------------------------------------------ storage
def _init_storage() -> str:
    global _storage_key
    if _storage_key:
        return _storage_key
    r = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": os.environ["EMERGENT_LLM_KEY"]}, timeout=30)
    r.raise_for_status()
    _storage_key = r.json()["storage_key"]
    return _storage_key


def _put(path: str, data: bytes, ctype: str) -> dict:
    global _storage_key
    for attempt in range(2):
        r = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": _init_storage(), "Content-Type": ctype}, data=data, timeout=120)
        if r.status_code == 503 and attempt == 0:
            _storage_key = None
            continue
        if r.status_code == 402:
            raise HTTPException(402, "Storage quota exhausted. Please try again later.")
        r.raise_for_status()
        return r.json()
    raise HTTPException(503, "Storage unavailable")


def _get(path: str):
    global _storage_key
    for attempt in range(2):
        r = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": _init_storage()}, timeout=60)
        if r.status_code == 503 and attempt == 0:
            _storage_key = None
            continue
        r.raise_for_status()
        return r.content, r.headers.get("Content-Type", "application/octet-stream")
    raise HTTPException(503, "Storage unavailable")


UPLOAD_RULES = {
    "property_photo": ({"image/jpeg", "image/png", "image/webp"}, 8 * 1024 * 1024, True),
    "broker_doc": ({"image/jpeg", "image/png", "image/webp", "application/pdf"}, 10 * 1024 * 1024, False),
}
EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "application/pdf": "pdf"}


@router.post("/uploads")
async def upload_file(file: UploadFile = File(...), kind: str = Form(...), user: dict = Depends(current_user)):
    if kind not in UPLOAD_RULES:
        raise HTTPException(400, "Unknown upload kind")
    allowed, max_size, is_public = UPLOAD_RULES[kind]
    ctype = (file.content_type or "").lower()
    if ctype == "image/jpg":
        ctype = "image/jpeg"
    if ctype not in allowed:
        raise HTTPException(400, "Unsupported file type")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > max_size:
        raise HTTPException(400, f"File too large (max {max_size // (1024 * 1024)} MB)")
    fid = uid("file")
    path = f"{APP_NAME}/{'photos' if is_public else 'private'}/{user['user_id']}/{fid}.{EXT[ctype]}"
    res = await run_in_threadpool(_put, path, data, ctype)
    doc = {"id": fid, "owner_id": user["user_id"], "kind": kind, "is_public": is_public, "storage_path": res["path"],
           "content_type": ctype, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
           "original_name": (file.filename or "")[:120], "is_deleted": False, "created_at": now()}
    await db.files.insert_one(doc)
    return {"id": fid, "url": f"/api/files/{fid}", "kind": kind, "content_type": ctype}


@router.get("/files/{file_id}")
async def get_file(file_id: str, request: Request, token: Optional[str] = None):
    f = await db.files.find_one({"id": file_id, "is_deleted": False}, {"_id": 0})
    if not f:
        raise HTTPException(404, "File not found")
    if not f["is_public"]:
        user = await current_user_optional(request)
        if not user and token:
            sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
            if sess and aware(sess["expires_at"]) > now():
                user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
        if not user or (user["user_id"] != f["owner_id"] and user.get("role") != "admin"):
            raise HTTPException(403, "Not allowed")
        if user.get("role") == "admin" and user["user_id"] != f["owner_id"]:
            await db.audit_logs.insert_one({"id": uid("aud"), "actor": user["user_id"], "action": "file.view_private",
                                            "target": file_id, "details": {}, "created_at": now()})
    data, ctype = await run_in_threadpool(_get, f["storage_path"])
    cache = "public, max-age=86400" if f["is_public"] else "private, no-store"
    return Response(content=data, media_type=f["content_type"] or ctype, headers={"Cache-Control": cache})


# ------------------------------------------------------------------ lister profile / broker verification
async def broker_profile(user_id: str) -> Optional[dict]:
    return await db.broker_profiles.find_one({"user_id": user_id}, {"_id": 0})


def broker_public(bp: Optional[dict]) -> Optional[dict]:
    if not bp:
        return None
    return {k: bp.get(k) for k in ("status", "full_name", "firm_name", "rera_number", "rera_status", "admin_note", "updated_at")} | {
        "updated_at": clean({"x": bp.get("updated_at")})["x"]}


@router.get("/me/lister")
async def me_lister(user: dict = Depends(current_user)):
    bp = await broker_profile(user["user_id"])
    return {"can_post_as_owner": True, "can_post_as_broker": bool(bp and bp["status"] == "approved"), "broker": broker_public(bp)}


class BrokerApplyIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    firm_name: Optional[str] = Field(default="", max_length=120)
    phone: str
    rera_number: Optional[str] = Field(default="", max_length=60)
    document_ids: List[str] = Field(min_length=1, max_length=5)
    declaration_accepted: bool


@router.post("/broker/apply")
async def broker_apply(body: BrokerApplyIn, user: dict = Depends(current_user)):
    if not body.declaration_accepted:
        raise HTTPException(400, "You must accept the declaration")
    phone = re.sub(r"\D", "", body.phone)[-10:]
    if not re.match(r"^[6-9]\d{9}$", phone):
        raise HTTPException(400, "Enter a valid 10-digit Indian mobile number")
    existing = await broker_profile(user["user_id"])
    if existing and existing["status"] in ("pending", "approved"):
        raise HTTPException(409, f"Broker request already {existing['status']}")
    if existing and existing["status"] == "suspended":
        raise HTTPException(403, "Your broker account is suspended. Contact support.")
    docs = await db.files.count_documents({"id": {"$in": body.document_ids}, "owner_id": user["user_id"], "kind": "broker_doc", "is_deleted": False})
    if docs != len(set(body.document_ids)):
        raise HTTPException(400, "Invalid documents")
    doc = {"user_id": user["user_id"], "status": "pending", "full_name": body.full_name.strip(), "firm_name": (body.firm_name or "").strip(),
           "phone": phone, "rera_number": (body.rera_number or "").strip(),
           "rera_status": "provided_unverified" if (body.rera_number or "").strip() else "not_provided",
           "document_ids": list(dict.fromkeys(body.document_ids)), "admin_note": None, "reviewed_by": None, "reviewed_at": None,
           "updated_at": now()}
    await db.broker_profiles.update_one({"user_id": user["user_id"]}, {"$set": doc, "$setOnInsert": {"created_at": now()}}, upsert=True)
    return broker_public(await broker_profile(user["user_id"]))


# ------------------------------------------------------------------ listings (owner / broker)
class ListingIn(BaseModel):
    posted_as: Literal["owner", "broker"]
    title_en: str = Field(min_length=5, max_length=100)
    title_hi: Optional[str] = Field(default="", max_length=100)
    description_en: str = Field(min_length=20, max_length=2000)
    description_hi: Optional[str] = Field(default="", max_length=2000)
    purpose: Literal["buy", "rent"]
    segment: str
    type: str
    locality_id: str
    price: int = Field(ge=1000, le=10_000_000_000)
    bhk: Optional[int] = Field(default=None, ge=1, le=20)
    bathrooms: Optional[int] = Field(default=None, ge=0, le=20)
    area_sqft: int = Field(ge=50, le=10_000_000)
    furnishing: Optional[Literal["furnished", "semi-furnished", "unfurnished"]] = None
    amenities: List[str] = []
    photo_ids: List[str] = Field(min_length=1, max_length=10)
    owner_declaration_accepted: bool


async def validate_listing(body: ListingIn, user: dict):
    if not body.owner_declaration_accepted:
        raise HTTPException(400, "You must accept the authority declaration")
    if body.posted_as == "broker":
        bp = await broker_profile(user["user_id"])
        if not bp or bp["status"] != "approved":
            raise HTTPException(403, "Broker posting requires an approved broker verification")
    if not await db.property_categories.find_one({"slug": body.segment, "kind": "segment"}):
        raise HTTPException(400, "Unknown category")
    pt = await db.property_types.find_one({"slug": body.type, "is_active": True})
    if not pt:
        raise HTTPException(400, "Unknown property type")
    if body.segment != "new-projects" and pt["segment"] != body.segment:
        raise HTTPException(400, "Property type does not match category")
    if pt.get("has_bhk") and not body.bhk and body.type != "pg-hostel":
        raise HTTPException(400, "BHK is required for this property type")
    loc = await db.localities.find_one({"id": body.locality_id, "is_active": True}, {"_id": 0})
    if not loc:
        raise HTTPException(400, "Unknown locality")
    if body.amenities:
        n = await db.amenities.count_documents({"slug": {"$in": body.amenities}, "is_active": True})
        if n != len(set(body.amenities)):
            raise HTTPException(400, "Unknown amenity")
    files = await db.files.find({"id": {"$in": body.photo_ids}, "owner_id": user["user_id"], "kind": "property_photo", "is_deleted": False}, {"_id": 0}).to_list(20)
    if len(files) != len(set(body.photo_ids)):
        raise HTTPException(400, "Invalid photos")
    return loc, files


def norm_title(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


async def find_duplicates(prop: dict, photo_hashes: List[str]) -> List[dict]:
    flags = {}
    cand = await db.properties.find({"id": {"$ne": prop["id"]}, "locality_id": prop["locality_id"], "purpose": prop["purpose"],
                                     "listing_status": {"$in": ["active", "pending_review", "changes_requested"]}}, {"_id": 0}).to_list(500)
    for c in cand:
        reasons = []
        if c.get("type") == prop["type"] and c.get("price") and c.get("area_sqft"):
            if abs(c["price"] - prop["price"]) <= 0.05 * prop["price"] and abs(c["area_sqft"] - prop["area_sqft"]) <= 0.05 * prop["area_sqft"]:
                reasons.append("similar price & area in same locality")
        if norm_title(c.get("title_en", "")) == norm_title(prop["title_en"]):
            reasons.append("same title in same locality")
        if c.get("owner_user_id") == prop["owner_user_id"] and c.get("type") == prop["type"] and c.get("bhk") == prop.get("bhk"):
            reasons.append("same lister posted similar property")
        if reasons:
            flags[c["id"]] = reasons
    if photo_hashes:
        same = await db.properties.find({"id": {"$ne": prop["id"]}, "photo_hashes": {"$in": photo_hashes}}, {"_id": 0, "id": 1}).to_list(50)
        for s in same:
            flags.setdefault(s["id"], []).append("identical photo used")
    return [{"property_id": k, "reasons": v} for k, v in flags.items()]


def listing_doc_from(body: ListingIn, files: List[dict]) -> dict:
    order = {pid: i for i, pid in enumerate(body.photo_ids)}
    files = sorted(files, key=lambda f: order[f["id"]])
    return {
        "title_en": body.title_en.strip(), "title_hi": (body.title_hi or "").strip() or body.title_en.strip(),
        "description_en": body.description_en.strip(), "description_hi": (body.description_hi or "").strip() or body.description_en.strip(),
        "purpose": body.purpose, "segment": body.segment, "type": body.type, "locality_id": body.locality_id,
        "price": body.price, "bhk": body.bhk, "bathrooms": body.bathrooms, "area_sqft": body.area_sqft,
        "furnishing": body.furnishing, "amenities": list(dict.fromkeys(body.amenities)),
        "images": [f"/api/files/{f['id']}" for f in files], "photo_ids": [f["id"] for f in files],
        "photo_hashes": [f["sha256"] for f in files], "posted_by_role": body.posted_as,
    }


def mine_view(p: dict) -> dict:
    d = clean(p)
    for k in ("photo_hashes", "demo_key"):
        d.pop(k, None)
    return d


@router.post("/listings")
async def create_listing(body: ListingIn, user: dict = Depends(current_user)):
    _, files = await validate_listing(body, user)
    city = await db.cities.find_one({"slug": "ujjain"})
    prop = {"id": uid("prop"), "is_demo": False, "city_id": city["id"], "owner_user_id": user["user_id"],
            "posted_by_name": user.get("name") or "Lister", **listing_doc_from(body, files),
            "listing_status": "pending_review", "verification_status": "unverified", "featured": False, "featured_until": None,
            "owner_declaration": {"accepted": True, "version": DECLARATION_VERSION, "at": now()},
            "moderation": None, "duplicate_flags": [], "created_at": now(), "updated_at": now()}
    prop["duplicate_flags"] = await find_duplicates(prop, prop["photo_hashes"])
    await db.properties.insert_one(prop)
    return mine_view(prop)


@router.get("/listings/mine")
async def my_listings(user: dict = Depends(current_user)):
    docs = await db.properties.find({"owner_user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    out = await enrich(docs)
    for o, d in zip(out, docs):
        o["listing_status"] = d["listing_status"]
        o["moderation"] = clean(d.get("moderation") or {}) or None
        o["photo_ids"] = d.get("photo_ids", [])
        o["featured_until"] = clean({"x": d.get("featured_until")})["x"]
        o.pop("photo_hashes", None)
        o.pop("duplicate_flags", None)
    leads = {x["_id"]: x["n"] async for x in db.enquiries.aggregate([{"$match": {"lister_user_id": user["user_id"]}}, {"$group": {"_id": "$property_id", "n": {"$sum": 1}}}])}
    for o in out:
        o["lead_count"] = leads.get(o["id"], 0)
    return {"items": out}


@router.get("/listings/{prop_id}/edit")
async def get_listing_for_edit(prop_id: str, user: dict = Depends(current_user)):
    p = await db.properties.find_one({"id": prop_id, "owner_user_id": user["user_id"]}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Listing not found")
    return mine_view(p)


@router.put("/listings/{prop_id}")
async def update_listing(prop_id: str, body: ListingIn, user: dict = Depends(current_user)):
    p = await db.properties.find_one({"id": prop_id, "owner_user_id": user["user_id"]}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Listing not found")
    if p["listing_status"] in ("sold_rented", "expired"):
        raise HTTPException(400, "This listing can no longer be edited")
    _, files = await validate_listing(body, user)
    upd = {**listing_doc_from(body, files), "listing_status": "pending_review", "updated_at": now(),
           "owner_declaration": {"accepted": True, "version": DECLARATION_VERSION, "at": now()}}
    upd["duplicate_flags"] = await find_duplicates({**p, **upd}, upd["photo_hashes"])
    await db.properties.update_one({"id": prop_id}, {"$set": upd})
    return mine_view(await db.properties.find_one({"id": prop_id}, {"_id": 0}))


# ------------------------------------------------------------------ admin moderation
class NoteIn(BaseModel):
    note: Optional[str] = Field(default="", max_length=1000)


async def audit(admin: dict, action: str, target: str, details: dict):
    await db.audit_logs.insert_one({"id": uid("aud"), "actor": admin["user_id"], "action": action, "target": target, "details": details, "created_at": now()})


@router.get("/admin/listings")
async def admin_listings(status: str = "pending_review", admin: dict = Depends(admin_user)):
    if status not in ("pending_review", "changes_requested", "active", "rejected"):
        raise HTTPException(400, "Unknown status")
    flt = {"listing_status": status, "is_demo": {"$ne": True}}
    docs = await db.properties.find(flt, {"_id": 0}).sort("updated_at", -1).to_list(200)
    out = await enrich(docs)
    owners = {u["user_id"]: u async for u in db.users.find({"user_id": {"$in": [d.get("owner_user_id") for d in docs]}}, {"_id": 0})}
    for o, d in zip(out, docs):
        u = owners.get(d.get("owner_user_id")) or {}
        o["listing_status"] = d["listing_status"]
        o["owner"] = {"user_id": u.get("user_id"), "name": u.get("name"), "email": u.get("email")}
        o["duplicate_flags"] = d.get("duplicate_flags", [])
        o["moderation"] = clean(d.get("moderation") or {}) or None
        o["owner_declaration"] = clean(d.get("owner_declaration") or {}) or None
        o.pop("photo_hashes", None)
    counts = {c["_id"]: c["n"] async for c in db.properties.aggregate([{"$match": {"is_demo": {"$ne": True}}}, {"$group": {"_id": "$listing_status", "n": {"$sum": 1}}}])}
    return {"items": out, "counts": counts}


async def moderate(prop_id: str, admin: dict, status: str, note: str, require_note: bool):
    if require_note and len((note or "").strip()) < 5:
        raise HTTPException(400, "Please add a note for the lister (min 5 characters)")
    p = await db.properties.find_one({"id": prop_id, "is_demo": {"$ne": True}}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Listing not found")
    if p["listing_status"] not in ("pending_review", "changes_requested", "active"):
        raise HTTPException(400, f"Cannot change a {p['listing_status']} listing")
    if status == "active" and p.get("posted_by_role") == "broker":
        bp = await broker_profile(p["owner_user_id"])
        if not bp or bp["status"] != "approved":
            raise HTTPException(400, "Broker is not approved; cannot publish broker listing")
    mod = {"status": status, "note": (note or "").strip(), "by": admin["user_id"], "at": now()}
    await db.properties.update_one({"id": prop_id}, {"$set": {"listing_status": status, "moderation": mod, "updated_at": now()},
                                                     "$push": {"moderation_history": mod}})
    await audit(admin, f"listing.{status}", prop_id, {"note": mod["note"]})
    return {"id": prop_id, "listing_status": status}


@router.post("/admin/listings/{prop_id}/approve")
async def admin_approve(prop_id: str, body: NoteIn, admin: dict = Depends(admin_user)):
    return await moderate(prop_id, admin, "active", body.note, False)


@router.post("/admin/listings/{prop_id}/reject")
async def admin_reject(prop_id: str, body: NoteIn, admin: dict = Depends(admin_user)):
    return await moderate(prop_id, admin, "rejected", body.note, True)


@router.post("/admin/listings/{prop_id}/request-changes")
async def admin_request_changes(prop_id: str, body: NoteIn, admin: dict = Depends(admin_user)):
    return await moderate(prop_id, admin, "changes_requested", body.note, True)


@router.get("/admin/brokers")
async def admin_brokers(status: str = "pending", admin: dict = Depends(admin_user)):
    docs = await db.broker_profiles.find({"status": status} if status != "all" else {}, {"_id": 0}).sort("updated_at", -1).to_list(200)
    users = {u["user_id"]: u async for u in db.users.find({"user_id": {"$in": [d["user_id"] for d in docs]}}, {"_id": 0})}
    files = {f["id"]: f async for f in db.files.find({"id": {"$in": [i for d in docs for i in d.get("document_ids", [])]}}, {"_id": 0})}
    out = []
    for d in docs:
        x = clean(d)
        u = users.get(d["user_id"], {})
        x["email"] = u.get("email")
        x["documents"] = [{"id": i, "url": f"/api/files/{i}", "content_type": files.get(i, {}).get("content_type"), "name": files.get(i, {}).get("original_name")} for i in d.get("document_ids", [])]
        out.append(x)
    counts = {c["_id"]: c["n"] async for c in db.broker_profiles.aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}])}
    return {"items": out, "counts": counts}


async def set_broker(user_id: str, admin: dict, status: str, note: str, allowed_from: tuple):
    bp = await broker_profile(user_id)
    if not bp:
        raise HTTPException(404, "Broker request not found")
    if bp["status"] not in allowed_from:
        raise HTTPException(400, f"Cannot change a {bp['status']} broker to {status}")
    await db.broker_profiles.update_one({"user_id": user_id}, {"$set": {"status": status, "admin_note": (note or "").strip() or None,
                                                                         "reviewed_by": admin["user_id"], "reviewed_at": now(), "updated_at": now()}})
    if status == "suspended":
        # unpublish live broker listings
        await db.properties.update_many({"owner_user_id": user_id, "posted_by_role": "broker", "listing_status": {"$in": ["active", "pending_review"]}},
                                        {"$set": {"listing_status": "changes_requested", "moderation": {"status": "changes_requested", "note": "Broker account suspended", "by": admin["user_id"], "at": now()}}})
    await audit(admin, f"broker.{status}", user_id, {"note": note})
    return broker_public(await broker_profile(user_id))


@router.post("/admin/brokers/{user_id}/approve")
async def admin_broker_approve(user_id: str, body: NoteIn, admin: dict = Depends(admin_user)):
    return await set_broker(user_id, admin, "approved", body.note, ("pending", "suspended"))


@router.post("/admin/brokers/{user_id}/reject")
async def admin_broker_reject(user_id: str, body: NoteIn, admin: dict = Depends(admin_user)):
    if len((body.note or "").strip()) < 5:
        raise HTTPException(400, "Please add a reason (min 5 characters)")
    return await set_broker(user_id, admin, "rejected", body.note, ("pending",))


@router.post("/admin/brokers/{user_id}/suspend")
async def admin_broker_suspend(user_id: str, body: NoteIn, admin: dict = Depends(admin_user)):
    if len((body.note or "").strip()) < 5:
        raise HTTPException(400, "Please add a reason (min 5 characters)")
    return await set_broker(user_id, admin, "suspended", body.note, ("approved",))


# ------------------------------------------------------------------ leads (privacy-safe)
def mask_phone(p: str) -> str:
    return f"{p[:2]}XXXXXX{p[-2:]}" if p and len(p) == 10 else "XXXXXXXXXX"


async def lead_view(e: dict, viewer: dict, prop: Optional[dict]) -> dict:
    consent = bool(e.get("share_phone_consent"))
    out = {k: e.get(k) for k in ("id", "property_id", "name", "intent", "status", "message", "share_phone_consent")}
    out["phone"] = e["phone"] if consent else None
    out["phone_masked"] = mask_phone(e["phone"])
    out["created_at"] = clean({"x": e.get("created_at")})["x"]
    out["follow_up_at"] = clean({"x": e.get("follow_up_at")})["x"]
    out["notes"] = [clean(n) for n in e.get("notes", [])]
    out["messages"] = [clean(m) for m in e.get("messages", [])]
    out["property"] = {"id": prop["id"], "title_en": prop["title_en"], "title_hi": prop["title_hi"], "images": prop["images"][:1],
                       "price": prop["price"], "purpose": prop["purpose"]} if prop else None
    me, other = viewer["user_id"], (e.get("lister_user_id") if viewer["user_id"] == e.get("user_id") else e.get("user_id"))
    out["blocked_by_me"] = bool(other and await db.blocks.find_one({"blocker_id": me, "blocked_id": other}))
    out["messaging_blocked"] = bool(other and await db.blocks.find_one({"$or": [{"blocker_id": me, "blocked_id": other}, {"blocker_id": other, "blocked_id": me}]}))
    return out


async def log_contact_access(viewer: dict, e: dict):
    if e.get("share_phone_consent"):
        await db.contact_access_logs.insert_one({"id": uid("cal"), "viewer_id": viewer["user_id"], "viewer_role": viewer.get("role"),
                                                 "enquiry_id": e["id"], "buyer_user_id": e["user_id"], "at": now()})


@router.get("/leads")
async def list_leads(status: Optional[str] = None, user: dict = Depends(current_user)):
    flt = {"lister_user_id": user["user_id"]}
    if status:
        flt["status"] = status
    docs = await db.enquiries.find(flt, {"_id": 0}).sort("created_at", -1).to_list(300)
    props = {p["id"]: p async for p in db.properties.find({"id": {"$in": [d["property_id"] for d in docs]}}, {"_id": 0})}
    out = []
    for d in docs:
        v = await lead_view(d, user, props.get(d["property_id"]))
        v["phone"] = None  # list view never returns full numbers; open the lead to reveal (audited)
        v.pop("notes")
        v["message_count"] = len(d.get("messages", []))
        out.append(v)
    counts = {c["_id"]: c["n"] async for c in db.enquiries.aggregate([{"$match": {"lister_user_id": user["user_id"]}}, {"$group": {"_id": "$status", "n": {"$sum": 1}}}])}
    return {"items": out, "counts": counts}


async def get_lead_for(user: dict, lead_id: str) -> dict:
    e = await db.enquiries.find_one({"id": lead_id}, {"_id": 0})
    if not e or (e.get("lister_user_id") != user["user_id"] and user.get("role") != "admin"):
        raise HTTPException(404, "Lead not found")
    return e


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, user: dict = Depends(current_user)):
    e = await get_lead_for(user, lead_id)
    await log_contact_access(user, e)
    prop = await db.properties.find_one({"id": e["property_id"]}, {"_id": 0})
    return await lead_view(e, user, prop)


class LeadUpdateIn(BaseModel):
    status: Optional[Literal["new", "contacted", "follow_up", "closed"]] = None
    follow_up_at: Optional[datetime] = None
    note: Optional[str] = Field(default=None, max_length=1000)


@router.patch("/leads/{lead_id}")
async def update_lead(lead_id: str, body: LeadUpdateIn, user: dict = Depends(current_user)):
    e = await get_lead_for(user, lead_id)
    if e.get("lister_user_id") != user["user_id"]:
        raise HTTPException(403, "Only the lister can update this lead")
    upd: dict = {"updated_at": now()}
    push = {}
    if body.status:
        upd["status"] = body.status
    if body.follow_up_at is not None:
        upd["follow_up_at"] = aware(body.follow_up_at)
        upd.setdefault("status", "follow_up")
    if body.note and body.note.strip():
        push["notes"] = {"id": uid("note"), "text": body.note.strip(), "at": now()}
    q = {"$set": upd}
    if push:
        q["$push"] = push
    await db.enquiries.update_one({"id": lead_id}, q)
    e = await db.enquiries.find_one({"id": lead_id}, {"_id": 0})
    prop = await db.properties.find_one({"id": e["property_id"]}, {"_id": 0})
    return await lead_view(e, user, prop)


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


PHONE_IN_TEXT = re.compile(r"(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}")


@router.post("/enquiries/{enq_id}/messages")
async def post_message(enq_id: str, body: MessageIn, user: dict = Depends(current_user)):
    e = await db.enquiries.find_one({"id": enq_id}, {"_id": 0})
    if not e:
        raise HTTPException(404, "Enquiry not found")
    if user["user_id"] == e["user_id"]:
        sender = "buyer"
    elif user["user_id"] == e.get("lister_user_id"):
        sender = "lister"
    else:
        raise HTTPException(404, "Enquiry not found")
    if await db.blocks.find_one({"$or": [{"blocker_id": e.get("user_id"), "blocked_id": e.get("lister_user_id")},
                                         {"blocker_id": e.get("lister_user_id"), "blocked_id": e.get("user_id")}]}):
        raise HTTPException(403, "Messaging is blocked for this conversation")
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Message is empty")
    msg = {"id": uid("msg"), "from": sender, "text": text, "at": now()}
    upd = {"$push": {"messages": msg}, "$set": {"updated_at": now()}}
    if sender == "lister" and e.get("status") == "new":
        upd["$set"]["status"] = "contacted"
    if sender == "buyer" and e.get("status") == "closed":
        upd["$set"]["status"] = "new"  # reopen so the lister notices the new message
    await db.enquiries.update_one({"id": enq_id}, upd)
    return clean(msg)


@router.get("/enquiries/{enq_id}")
async def buyer_enquiry(enq_id: str, user: dict = Depends(current_user)):
    e = await db.enquiries.find_one({"id": enq_id, "user_id": user["user_id"]}, {"_id": 0})
    if not e:
        raise HTTPException(404, "Enquiry not found")
    prop = await db.properties.find_one({"id": e["property_id"]}, {"_id": 0})
    out = await lead_view(e, user, prop)
    out["phone"] = e["phone"]  # buyer's own number
    out.pop("notes")  # lister's private notes
    out.pop("follow_up_at", None)  # lister's private CRM data
    out["status"] = "closed" if e.get("status") == "closed" else ("replied" if any(m.get("from") == "lister" for m in e.get("messages", [])) else "sent")
    return out


@router.post("/enquiries/{enq_id}/report")
async def report_enquiry(enq_id: str, body: NoteIn, user: dict = Depends(current_user)):
    e = await db.enquiries.find_one({"id": enq_id}, {"_id": 0})
    if not e or user["user_id"] not in (e["user_id"], e.get("lister_user_id")):
        raise HTTPException(404, "Enquiry not found")
    await db.abuse_reports.insert_one({"id": uid("abuse"), "enquiry_id": enq_id, "reporter_id": user["user_id"], "note": (body.note or "").strip(), "status": "open", "created_at": now()})
    return {"reported": True}


@router.get("/admin/contact-access-logs")
async def admin_access_logs(admin: dict = Depends(admin_user)):
    docs = await db.contact_access_logs.find({}, {"_id": 0}).sort("at", -1).to_list(200)
    return {"items": [clean(d) for d in docs]}


# ------------------------------------------------------------------ featured plans + Razorpay
DEFAULT_PLANS = [
    {"slug": "featured-15d-299", "name_en": "Featured · 15 days", "name_hi": "फ़ीचर्ड · 15 दिन", "price_inr": 299, "duration_days": 15, "order": 1},
    {"slug": "featured-30d-499", "name_en": "Featured · 30 days", "name_hi": "फ़ीचर्ड · 30 दिन", "price_inr": 499, "duration_days": 30, "order": 2},
]
LEGACY_PLAN_SLUGS = ["featured-30", "featured-45"]


async def seed_marketplace():
    await db.files.create_index("id", unique=True)
    await db.broker_profiles.create_index("user_id", unique=True)
    await db.featured_plans.create_index("slug", unique=True)
    await db.payment_orders.create_index("id", unique=True)
    await db.payment_orders.create_index("razorpay_order_id", unique=True)
    await db.payment_webhook_events.create_index("event_id", unique=True)
    await db.enquiries.create_index([("lister_user_id", 1), ("created_at", -1)])
    await db.properties.create_index("owner_user_id")
    await db.properties.create_index("photo_hashes")
    for p in DEFAULT_PLANS:
        await db.featured_plans.update_one({"slug": p["slug"]}, {"$setOnInsert": {**p, "id": uid("plan"), "is_active": True, "created_at": now()}}, upsert=True)
    # Retire the earlier seeded plans unless an admin has edited them.
    await db.featured_plans.update_many({"slug": {"$in": LEGACY_PLAN_SLUGS}, "updated_at": {"$exists": False}}, {"$set": {"is_active": False}})
    await db.app_settings.update_one({"key": "commission"}, {"$setOnInsert": {"key": "commission", "default_rate_percent": 1.0,
                                     "auto_charge": False, "requires_written_agreement": True, "updated_at": now()}}, upsert=True)


async def expire_featured():
    await db.properties.update_many({"featured": True, "featured_until": {"$ne": None, "$lt": now()}}, {"$set": {"featured": False}})


def rzp_keys():
    kid, secret = os.environ.get("RAZORPAY_KEY_ID", "").strip(), os.environ.get("RAZORPAY_KEY_SECRET", "").strip()
    if not kid or not secret:
        raise HTTPException(503, "Payments are not configured yet")
    return kid, secret


def rzp_mode(kid: str) -> str:
    return "test" if kid.startswith("rzp_test_") else "live"


@router.get("/featured-plans")
async def featured_plans():
    docs = await db.featured_plans.find({"is_active": True}, {"_id": 0}).sort("order", 1).to_list(20)
    configured = bool(os.environ.get("RAZORPAY_KEY_ID", "").strip() and os.environ.get("RAZORPAY_KEY_SECRET", "").strip())
    mode = rzp_mode(os.environ.get("RAZORPAY_KEY_ID", "")) if configured else None
    return {"items": [clean(d) for d in docs], "payments_configured": configured, "mode": mode}


class OrderIn(BaseModel):
    property_id: str
    plan_id: str


@router.post("/payments/featured/order")
async def create_featured_order(body: OrderIn, request: Request, user: dict = Depends(current_user)):
    # Store policy: Featured is not sold inside the Android/iOS store apps (web only) until compliant billing is approved.
    if request.headers.get("x-lv-client", "").lower() != "web":
        raise HTTPException(403, "Featured purchases are available on the web only")
    kid, secret = rzp_keys()
    p = await db.properties.find_one({"id": body.property_id, "owner_user_id": user["user_id"]}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Listing not found")
    if p["listing_status"] != "active":
        raise HTTPException(400, "Only approved, live listings can be featured")
    plan = await db.featured_plans.find_one({"id": body.plan_id, "is_active": True}, {"_id": 0})
    if not plan:
        raise HTTPException(400, "Plan not available")
    amount = int(plan["price_inr"]) * 100
    oid = uid("pay")
    async with httpx.AsyncClient(timeout=20) as hc:
        r = await hc.post(f"{RZP_API}/orders", auth=(kid, secret), json={
            "amount": amount, "currency": "INR", "receipt": oid,
            "notes": {"property_id": p["id"], "plan": plan["slug"], "user_id": user["user_id"]}})
    if r.status_code >= 400:
        logger.error("Razorpay order failed: %s", r.status_code)
        raise HTTPException(502, "Could not start payment. Please try again.")
    rp = r.json()
    doc = {"id": oid, "user_id": user["user_id"], "property_id": p["id"], "plan_id": plan["id"], "plan_slug": plan["slug"],
           "duration_days": plan["duration_days"], "amount": amount, "currency": "INR", "razorpay_order_id": rp["id"],
           "razorpay_payment_id": None, "status": "created", "mode": rzp_mode(kid), "created_at": now(), "updated_at": now()}
    await db.payment_orders.insert_one(doc)
    return {"order_id": oid, "razorpay_order_id": rp["id"], "key_id": kid, "amount": amount, "currency": "INR",
            "mode": doc["mode"], "name": "LANDVILLA", "description": plan["name_en"], "prefill": {"email": user.get("email"), "name": user.get("name")}}


async def fulfil(order: dict, payment_id: str, source: str) -> dict:
    """Idempotent: only the first transition to 'paid' extends featured time."""
    upd = await db.payment_orders.find_one_and_update(
        {"id": order["id"], "status": {"$ne": "paid"}},
        {"$set": {"status": "paid", "razorpay_payment_id": payment_id, "paid_at": now(), "paid_via": source, "updated_at": now()}},
        return_document=ReturnDocument.AFTER)
    if not upd:
        return await db.payment_orders.find_one({"id": order["id"]}, {"_id": 0})
    p = await db.properties.find_one({"id": order["property_id"]}, {"_id": 0})
    start = aware(p.get("featured_until")) if p and p.get("featured_until") and aware(p["featured_until"]) > now() else now()
    until = start + timedelta(days=order["duration_days"])
    await db.properties.update_one({"id": order["property_id"]}, {"$set": {"featured": True, "featured_until": until, "updated_at": now()}})
    await db.payment_orders.update_one({"id": order["id"]}, {"$set": {"featured_until": until}})
    return await db.payment_orders.find_one({"id": order["id"]}, {"_id": 0})


class VerifyPayIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def pay_view(o: dict) -> dict:
    return {k: clean(o).get(k) for k in ("id", "property_id", "plan_slug", "amount", "status", "mode", "featured_until", "created_at", "paid_at", "failure_reason")}


@router.post("/payments/featured/verify")
async def verify_featured(body: VerifyPayIn, user: dict = Depends(current_user)):
    kid, secret = rzp_keys()
    order = await db.payment_orders.find_one({"razorpay_order_id": body.razorpay_order_id, "user_id": user["user_id"]}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Unknown order")
    expected = hmac.new(secret.encode(), f"{order['razorpay_order_id']}|{body.razorpay_payment_id}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, body.razorpay_signature):
        await db.payment_orders.update_one({"id": order["id"], "status": "created"}, {"$set": {"status": "verification_failed", "updated_at": now()}})
        raise HTTPException(400, "Payment verification failed")
    # Double-check with Razorpay that the payment really belongs to this order with the right amount.
    async with httpx.AsyncClient(timeout=20) as hc:
        r = await hc.get(f"{RZP_API}/payments/{body.razorpay_payment_id}", auth=(kid, secret))
    if r.status_code != 200:
        raise HTTPException(502, "Could not confirm payment. It will be confirmed automatically shortly.")
    pay = r.json()
    if pay.get("order_id") != order["razorpay_order_id"] or int(pay.get("amount", 0)) != order["amount"] or pay.get("currency") != "INR":
        raise HTTPException(400, "Payment does not match order")
    if pay.get("status") not in ("captured", "authorized"):
        if pay.get("status") == "failed":
            await db.payment_orders.update_one({"id": order["id"], "status": {"$ne": "paid"}}, {"$set": {"status": "failed", "failure_reason": pay.get("error_description"), "updated_at": now()}})
            raise HTTPException(400, "Payment failed")
        await db.payment_orders.update_one({"id": order["id"], "status": {"$ne": "paid"}}, {"$set": {"status": "pending", "updated_at": now()}})
        return pay_view(await db.payment_orders.find_one({"id": order["id"]}, {"_id": 0}))
    return pay_view(await fulfil(order, body.razorpay_payment_id, "checkout"))


class FailIn(BaseModel):
    razorpay_order_id: str
    reason: Literal["cancelled", "failed"] = "cancelled"
    description: Optional[str] = Field(default="", max_length=300)


@router.post("/payments/featured/failed")
async def mark_failed(body: FailIn, user: dict = Depends(current_user)):
    o = await db.payment_orders.find_one_and_update(
        {"razorpay_order_id": body.razorpay_order_id, "user_id": user["user_id"], "status": {"$in": ["created", "pending"]}},
        {"$set": {"status": body.reason, "failure_reason": (body.description or "")[:300], "updated_at": now()}}, return_document=ReturnDocument.AFTER)
    if not o:
        o = await db.payment_orders.find_one({"razorpay_order_id": body.razorpay_order_id, "user_id": user["user_id"]}, {"_id": 0})
        if not o:
            raise HTTPException(404, "Unknown order")
    return pay_view(o)


@router.get("/payments/mine")
async def my_payments(user: dict = Depends(current_user)):
    docs = await db.payment_orders.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"items": [pay_view(d) for d in docs]}


@router.post("/payments/razorpay/webhook")
async def razorpay_webhook(request: Request):
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(503, "Webhook not configured")
    raw = await request.body()
    sig = request.headers.get("x-razorpay-signature", "")
    if not hmac.compare_digest(hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest(), sig):
        raise HTTPException(400, "Invalid signature")
    event_id = request.headers.get("x-razorpay-event-id") or hashlib.sha256(raw).hexdigest()
    try:
        await db.payment_webhook_events.insert_one({"event_id": event_id, "received_at": now()})
    except DuplicateKeyError:
        return {"ok": True, "duplicate": True}
    payload = json.loads(raw)
    event = payload.get("event")
    entity = (payload.get("payload", {}).get("payment") or {}).get("entity") or {}
    order = await db.payment_orders.find_one({"razorpay_order_id": entity.get("order_id")}, {"_id": 0}) if entity else None
    if order and event in ("payment.captured", "payment.authorized", "order.paid"):
        if int(entity.get("amount", 0)) == order["amount"] and entity.get("currency") == "INR":
            await fulfil(order, entity["id"], "webhook")
    elif order and event == "payment.failed":
        await db.payment_orders.update_one({"id": order["id"], "status": {"$in": ["created", "pending"]}},
                                           {"$set": {"status": "failed", "failure_reason": entity.get("error_description"), "updated_at": now()}})
    return {"ok": True}


class PlanIn(BaseModel):
    name_en: str = Field(min_length=3, max_length=60)
    name_hi: str = Field(min_length=1, max_length=60)
    price_inr: int = Field(ge=1, le=100000)
    duration_days: int = Field(ge=1, le=365)
    is_active: bool = True


@router.get("/admin/featured-plans")
async def admin_plans(admin: dict = Depends(admin_user)):
    docs = await db.featured_plans.find({}, {"_id": 0}).sort("order", 1).to_list(50)
    return {"items": [clean(d) for d in docs]}


@router.put("/admin/featured-plans/{plan_id}")
async def admin_update_plan(plan_id: str, body: PlanIn, admin: dict = Depends(admin_user)):
    r = await db.featured_plans.update_one({"id": plan_id}, {"$set": {**body.model_dump(), "updated_at": now()}})
    if not r.matched_count:
        raise HTTPException(404, "Plan not found")
    await audit(admin, "plan.update", plan_id, body.model_dump())
    return clean(await db.featured_plans.find_one({"id": plan_id}, {"_id": 0}))


@router.post("/admin/featured-plans")
async def admin_create_plan(body: PlanIn, admin: dict = Depends(admin_user)):
    slug = f"featured-{body.duration_days}-{body.price_inr}"
    if await db.featured_plans.find_one({"slug": slug}):
        raise HTTPException(409, "A plan with this price and duration exists")
    n = await db.featured_plans.count_documents({})
    doc = {**body.model_dump(), "id": uid("plan"), "slug": slug, "order": n + 1, "created_at": now()}
    await db.featured_plans.insert_one(doc)
    await audit(admin, "plan.create", doc["id"], body.model_dump())
    return clean(doc)


@router.get("/admin/payments")
async def admin_payments(admin: dict = Depends(admin_user)):
    docs = await db.payment_orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": [pay_view(d) | {"user_id": d["user_id"]} for d in docs]}


@router.get("/admin/stats")
async def admin_stats(admin: dict = Depends(admin_user)):
    return {
        "pending_listings": await db.properties.count_documents({"listing_status": "pending_review"}),
        "pending_brokers": await db.broker_profiles.count_documents({"status": "pending"}),
        "open_reports": await db.abuse_reports.count_documents({"status": "open"}),
        "paid_orders": await db.payment_orders.count_documents({"status": "paid"}),
    }
