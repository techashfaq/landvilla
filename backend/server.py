import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from seed import norm, seed_all  # noqa: E402

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}
SEED_DEMO = os.environ.get("SEED_DEMO_LISTINGS", "false").lower() == "true"
SEED_TEST_SESSIONS = os.environ.get("SEED_TEST_SESSIONS", "false").lower() == "true"
EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("landvilla")

app = FastAPI(title="LANDVILLA API")


@app.get("/health", include_in_schema=False)
@app.head("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}


api = APIRouter(prefix="/api")


def now():
    return datetime.now(timezone.utc)


def aware(dt):
    if isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def iso(dt):
    dt = aware(dt)
    return dt.isoformat() if isinstance(dt, datetime) else dt


def clean(doc: Optional[dict]) -> Optional[dict]:
    """Strip Mongo _id and serialize datetimes."""
    if not doc:
        return doc
    out = {}
    for k, v in doc.items():
        if k == "_id":
            continue
        out[k] = iso(v) if isinstance(v, datetime) else v
    return out


# ------------------------------------------------------------------ auth
async def current_user_optional(request: Request) -> Optional[dict]:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not sess or aware(sess["expires_at"]) < now():
        return None
    user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
    return user


async def current_user(request: Request) -> dict:
    user = await current_user_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def admin_user(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def public_user(u: dict) -> dict:
    return {k: u.get(k) for k in ("user_id", "email", "name", "picture", "role")}


class SessionIn(BaseModel):
    session_id: str


@api.post("/auth/session")
async def auth_session(body: SessionIn):
    async with httpx.AsyncClient(timeout=15) as hc:
        r = await hc.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": body.session_id})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")
    data = r.json()
    email = data["email"].lower()
    role = "admin" if email in ADMIN_EMAILS else "buyer"
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        upd = {"name": data.get("name"), "picture": data.get("picture"), "updated_at": now()}
        if role == "admin":
            upd["role"] = "admin"
        await db.users.update_one({"user_id": user_id}, {"$set": upd})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({"user_id": user_id, "email": email, "name": data.get("name"),
                                   "picture": data.get("picture"), "role": role, "created_at": now()})
    token = data["session_token"]
    await db.user_sessions.update_one(
        {"session_token": token},
        {"$set": {"session_token": token, "user_id": user_id, "expires_at": now() + timedelta(days=7), "created_at": now()}},
        upsert=True,
    )
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return {"session_token": token, "user": public_user(user)}


@api.get("/auth/me")
async def auth_me(user: dict = Depends(current_user)):
    return public_user(user)


@api.post("/auth/logout")
async def auth_logout(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        await db.user_sessions.delete_one({"session_token": auth[7:].strip()})
    return {"ok": True}


# ------------------------------------------------------------------ meta
async def get_city(slug: str = "ujjain") -> dict:
    city = await db.cities.find_one({"slug": slug, "is_active": True}, {"_id": 0})
    if not city:
        raise HTTPException(404, "City not found")
    return city


def loc_public(l: dict) -> dict:
    return {k: l.get(k) for k in ("id", "slug", "name_en", "name_hi", "zone_id", "parent_id", "aliases",
                                  "verification_status", "is_active")}


@api.get("/meta")
async def meta(city: str = "ujjain"):
    c = await get_city(city)
    zones = await db.zones.find({"city_id": c["id"], "is_active": True}, {"_id": 0}).sort("order", 1).to_list(100)
    locs = await db.localities.find({"city_id": c["id"], "is_active": True}, {"_id": 0}).sort("name_en", 1).to_list(1000)
    cats = await db.property_categories.find({"is_active": True}, {"_id": 0}).sort("order", 1).to_list(100)
    types = await db.property_types.find({"is_active": True}, {"_id": 0}).sort("order", 1).to_list(100)
    ams = await db.amenities.find({"is_active": True}, {"_id": 0}).sort("order", 1).to_list(100)
    return {
        "city": clean(c),
        "zones": [clean(z) for z in zones],
        "localities": [loc_public(l) for l in locs],
        "categories": [clean(x) for x in cats],
        "property_types": [clean(x) for x in types],
        "amenities": [clean(x) for x in ams],
    }


# ------------------------------------------------------------------ properties
async def enrich(props: List[dict], user: Optional[dict] = None) -> List[dict]:
    loc_ids = list({p["locality_id"] for p in props})
    locs = {l["id"]: l async for l in db.localities.find({"id": {"$in": loc_ids}}, {"_id": 0})}
    zone_ids = list({l.get("zone_id") for l in locs.values() if l.get("zone_id")})
    zones = {z["id"]: z async for z in db.zones.find({"id": {"$in": zone_ids}}, {"_id": 0})}
    saved = set()
    if user:
        saved = {s["property_id"] async for s in db.saved.find({"user_id": user["user_id"]}, {"_id": 0, "property_id": 1})}
    out = []
    for p in props:
        d = clean(p)
        d.pop("demo_key", None)
        l = locs.get(p["locality_id"])
        d["locality"] = loc_public(l) if l else None
        z = zones.get(l.get("zone_id")) if l else None
        d["zone"] = {"id": z["id"], "slug": z["slug"], "name_en": z["name_en"], "name_hi": z["name_hi"]} if z else None
        d["is_saved"] = p["id"] in saved
        out.append(d)
    return out


@api.get("/properties")
async def search_properties(
    request: Request,
    purpose: Optional[str] = Query(None, pattern="^(buy|rent)$"),
    segment: Optional[str] = None,
    type: Optional[str] = None,
    locality: Optional[str] = None,
    zone: Optional[str] = None,
    min_price: Optional[int] = Query(None, ge=0),
    max_price: Optional[int] = Query(None, ge=0),
    bhk: Optional[str] = None,
    q: Optional[str] = None,
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
):
    city = await get_city()
    flt: dict = {"listing_status": "active", "city_id": city["id"]}
    if purpose:
        flt["purpose"] = purpose
    if segment:
        if not await db.property_categories.find_one({"slug": segment, "kind": "segment"}):
            raise HTTPException(400, "Unknown category")
        flt["segment"] = segment
    if type:
        if not await db.property_types.find_one({"slug": type}):
            raise HTTPException(400, "Unknown property type")
        flt["type"] = type
    loc_filter_ids = None
    if locality:
        ids = [x.strip() for x in locality.split(",") if x.strip()]
        found = await db.localities.find({"city_id": city["id"], "is_active": True,
                                          "$or": [{"id": {"$in": ids}}, {"slug": {"$in": ids}}]},
                                         {"_id": 0, "id": 1}).to_list(100)
        if not found:
            raise HTTPException(400, "Unknown locality")
        loc_filter_ids = {f["id"] for f in found}
        # include child localities
        children = await db.localities.find({"parent_id": {"$in": list(loc_filter_ids)}, "is_active": True}, {"_id": 0, "id": 1}).to_list(100)
        loc_filter_ids |= {c["id"] for c in children}
    if zone:
        z = await db.zones.find_one({"city_id": city["id"], "$or": [{"id": zone}, {"slug": zone}]})
        if not z:
            raise HTTPException(400, "Unknown zone")
        zl = {l["id"] async for l in db.localities.find({"zone_id": z["id"], "is_active": True}, {"_id": 0, "id": 1})}
        loc_filter_ids = zl if loc_filter_ids is None else (loc_filter_ids & zl)
    if q:
        nq = norm(q)
        rx = re.escape(nq)
        ql = {l["id"] async for l in db.localities.find(
            {"city_id": city["id"], "is_active": True, "search_keys": {"$regex": rx, "$options": "i"}}, {"_id": 0, "id": 1})}
        flt["$or"] = [{"title_en": {"$regex": rx, "$options": "i"}}, {"title_hi": {"$regex": re.escape(q.strip())}},
                      {"locality_id": {"$in": list(ql)}}]
    if loc_filter_ids is not None:
        flt["locality_id"] = {"$in": list(loc_filter_ids)}
    if min_price is not None or max_price is not None:
        pr = {}
        if min_price is not None:
            pr["$gte"] = min_price
        if max_price is not None:
            pr["$lte"] = max_price
        flt["price"] = pr
    if bhk:
        vals = []
        for b in bhk.split(","):
            b = b.strip()
            if b == "4+":
                vals.append({"bhk": {"$gte": 4}})
            elif b.isdigit():
                vals.append({"bhk": int(b)})
        if vals:
            flt.setdefault("$and", []).append({"$or": vals})
    sort_spec = {"newest": [("featured", -1), ("created_at", -1)], "price_asc": [("price", 1)], "price_desc": [("price", -1)]}[sort]
    total = await db.properties.count_documents(flt)
    docs = await db.properties.find(flt, {"_id": 0}).sort(sort_spec).skip((page - 1) * limit).limit(limit).to_list(limit)
    user = await current_user_optional(request)
    return {"items": await enrich(docs, user), "total": total, "page": page, "limit": limit}


@api.get("/properties/{prop_id}")
async def property_detail(prop_id: str, request: Request):
    p = await db.properties.find_one({"id": prop_id, "listing_status": "active"}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Property not found")
    user = await current_user_optional(request)
    return (await enrich([p], user))[0]


# ------------------------------------------------------------------ saved
@api.get("/saved")
async def list_saved(user: dict = Depends(current_user)):
    ids = [s["property_id"] async for s in db.saved.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1)]
    docs = await db.properties.find({"id": {"$in": ids}, "listing_status": "active"}, {"_id": 0}).to_list(200)
    order = {pid: i for i, pid in enumerate(ids)}
    docs.sort(key=lambda d: order.get(d["id"], 0))
    return {"items": await enrich(docs, user)}


@api.post("/saved/{prop_id}")
async def save_prop(prop_id: str, user: dict = Depends(current_user)):
    if not await db.properties.find_one({"id": prop_id, "listing_status": "active"}):
        raise HTTPException(404, "Property not found")
    await db.saved.update_one({"user_id": user["user_id"], "property_id": prop_id},
                              {"$setOnInsert": {"created_at": now()}}, upsert=True)
    return {"saved": True}


@api.delete("/saved/{prop_id}")
async def unsave_prop(prop_id: str, user: dict = Depends(current_user)):
    await db.saved.delete_one({"user_id": user["user_id"], "property_id": prop_id})
    return {"saved": False}


# ------------------------------------------------------------------ enquiries
PHONE_RX = re.compile(r"^[6-9]\d{9}$")


class EnquiryIn(BaseModel):
    property_id: str
    name: str = Field(min_length=2, max_length=80)
    phone: str
    message: Optional[str] = Field(default="", max_length=500)
    intent: str = Field(default="info", pattern="^(info|site_visit|callback)$")

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        digits = re.sub(r"\D", "", v)
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        if not PHONE_RX.match(digits):
            raise ValueError("Enter a valid 10-digit Indian mobile number")
        return digits

    @field_validator("name")
    @classmethod
    def check_name(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name is too short")
        return v


@api.post("/enquiries")
async def create_enquiry(body: EnquiryIn, user: dict = Depends(current_user)):
    p = await db.properties.find_one({"id": body.property_id, "listing_status": "active"}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Property not found")
    recent = await db.enquiries.find_one({"user_id": user["user_id"], "property_id": body.property_id,
                                          "created_at": {"$gte": now() - timedelta(hours=24)}})
    if recent:
        raise HTTPException(409, "You already sent an enquiry for this property in the last 24 hours")
    doc = {"id": f"enq_{uuid.uuid4().hex[:12]}", "user_id": user["user_id"], "property_id": body.property_id,
           "name": body.name, "phone": body.phone, "message": (body.message or "").strip(), "intent": body.intent,
           "status": "new", "is_demo_property": bool(p.get("is_demo")), "created_at": now()}
    await db.enquiries.insert_one(doc)
    return clean(doc)


@api.get("/enquiries/me")
async def my_enquiries(user: dict = Depends(current_user)):
    docs = await db.enquiries.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    pids = list({d["property_id"] for d in docs})
    props = await db.properties.find({"id": {"$in": pids}}, {"_id": 0}).to_list(200)
    pmap = {p["id"]: p for p in await enrich(props)}
    out = []
    for d in docs:
        x = clean(d)
        x["property"] = pmap.get(d["property_id"])
        out.append(x)
    return {"items": out}


# ------------------------------------------------------------------ admin: localities
async def audit(admin: dict, action: str, target: str, details: dict):
    await db.audit_logs.insert_one({"id": f"aud_{uuid.uuid4().hex[:12]}", "actor": admin["user_id"], "action": action,
                                    "target": target, "details": details, "created_at": now()})


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


class LocalityIn(BaseModel):
    name_en: str = Field(min_length=2, max_length=80)
    name_hi: str = Field(min_length=1, max_length=80)
    zone_id: Optional[str] = None
    parent_id: Optional[str] = None
    aliases: List[str] = []
    source: str = Field(default="admin_entry", max_length=200)


class LocalityPatch(BaseModel):
    name_en: Optional[str] = Field(default=None, min_length=2, max_length=80)
    name_hi: Optional[str] = Field(default=None, min_length=1, max_length=80)
    zone_id: Optional[str] = None
    parent_id: Optional[str] = None
    aliases: Optional[List[str]] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    geocode_source: Optional[str] = None


class VerifyIn(BaseModel):
    source: str = Field(min_length=3, max_length=300)


class MergeIn(BaseModel):
    source_id: str
    target_id: str


def keys_for(name_en, name_hi, aliases):
    return sorted({norm(name_en), name_hi, *[norm(a) for a in aliases if a.strip()]})


async def check_key_conflicts(city_id, keys, exclude_id=None):
    flt = {"city_id": city_id, "search_keys": {"$in": keys}, "is_active": True}
    if exclude_id:
        flt["id"] = {"$ne": exclude_id}
    clash = await db.localities.find_one(flt, {"_id": 0, "name_en": 1})
    if clash:
        raise HTTPException(409, f"Name or alias conflicts with existing locality '{clash['name_en']}'")


@api.get("/admin/localities")
async def admin_list_localities(q: Optional[str] = None, include_inactive: bool = True, admin: dict = Depends(admin_user)):
    city = await get_city()
    flt: dict = {"city_id": city["id"]}
    if not include_inactive:
        flt["is_active"] = True
    if q:
        flt["search_keys"] = {"$regex": re.escape(norm(q)), "$options": "i"}
    docs = await db.localities.find(flt, {"_id": 0, "search_keys": 0}).sort("name_en", 1).to_list(1000)
    counts = {c["_id"]: c["n"] async for c in db.properties.aggregate([{"$group": {"_id": "$locality_id", "n": {"$sum": 1}}}])}
    return {"items": [{**clean(d), "listing_count": counts.get(d["id"], 0)} for d in docs]}


@api.post("/admin/localities")
async def admin_create_locality(body: LocalityIn, admin: dict = Depends(admin_user)):
    city = await get_city()
    slug = slugify(body.name_en)
    if await db.localities.find_one({"city_id": city["id"], "slug": slug}):
        raise HTTPException(409, "A locality with this name already exists")
    keys = keys_for(body.name_en, body.name_hi, body.aliases)
    await check_key_conflicts(city["id"], keys)
    if body.zone_id and not await db.zones.find_one({"id": body.zone_id}):
        raise HTTPException(400, "Unknown zone")
    if body.parent_id and not await db.localities.find_one({"id": body.parent_id, "is_active": True}):
        raise HTTPException(400, "Unknown parent locality")
    doc = {"id": f"loc_{uuid.uuid4().hex[:12]}", "city_id": city["id"], "slug": slug, "name_en": body.name_en.strip(),
           "name_hi": body.name_hi.strip(), "aliases": body.aliases, "search_keys": keys, "zone_id": body.zone_id,
           "zone_assignment": "tentative" if body.zone_id else "unassigned", "parent_id": body.parent_id,
           "is_active": True, "source": body.source, "verification_status": "unverified", "last_verified_at": None,
           "verified_by": None, "latitude": None, "longitude": None, "geocode_source": None, "merged_into": None,
           "created_at": now(), "updated_at": now()}
    await db.localities.insert_one(doc)
    await audit(admin, "locality.create", doc["id"], {"name_en": doc["name_en"]})
    d = clean(doc)
    d.pop("search_keys", None)
    return d


@api.patch("/admin/localities/{loc_id}")
async def admin_edit_locality(loc_id: str, body: LocalityPatch, admin: dict = Depends(admin_user)):
    loc = await db.localities.find_one({"id": loc_id}, {"_id": 0})
    if not loc:
        raise HTTPException(404, "Locality not found")
    upd = body.model_dump(exclude_unset=True)
    if ("latitude" in upd or "longitude" in upd) and not upd.get("geocode_source"):
        raise HTTPException(400, "Coordinates require a verified geocode_source")
    if upd.get("zone_id") and not await db.zones.find_one({"id": upd["zone_id"]}):
        raise HTTPException(400, "Unknown zone")
    if upd.get("parent_id"):
        if upd["parent_id"] == loc_id or not await db.localities.find_one({"id": upd["parent_id"]}):
            raise HTTPException(400, "Invalid parent locality")
        # prevent parent loops: walk up the ancestor chain
        cur, hops = upd["parent_id"], 0
        while cur and hops < 50:
            if cur == loc_id:
                raise HTTPException(400, "Parent would create a loop")
            anc = await db.localities.find_one({"id": cur}, {"_id": 0, "parent_id": 1})
            cur, hops = (anc or {}).get("parent_id"), hops + 1
    merged = {**loc, **upd}
    keys = keys_for(merged["name_en"], merged["name_hi"], merged.get("aliases") or [])
    await check_key_conflicts(loc["city_id"], keys, exclude_id=loc_id)
    upd["search_keys"] = keys
    changed = {k for k in ("name_en", "name_hi", "zone_id", "latitude", "longitude") if k in upd and upd[k] != loc.get(k)}
    if "zone_id" in changed:
        upd["zone_assignment"] = "tentative" if upd["zone_id"] else "unassigned"
    # changing core facts resets verification
    if changed and loc["verification_status"] == "verified":
        upd["verification_status"] = "pending"
    upd["updated_at"] = now()
    await db.localities.update_one({"id": loc_id}, {"$set": upd})
    await audit(admin, "locality.edit", loc_id, {k: v for k, v in upd.items() if k not in ("search_keys", "updated_at")})
    doc = await db.localities.find_one({"id": loc_id}, {"_id": 0, "search_keys": 0})
    return clean(doc)


@api.post("/admin/localities/{loc_id}/verify")
async def admin_verify_locality(loc_id: str, body: VerifyIn, admin: dict = Depends(admin_user)):
    loc = await db.localities.find_one({"id": loc_id})
    if not loc:
        raise HTTPException(404, "Locality not found")
    await db.localities.update_one({"id": loc_id}, {"$set": {
        "verification_status": "verified", "last_verified_at": now(), "verified_by": admin["user_id"],
        "source": body.source, "zone_assignment": "verified" if loc.get("zone_id") else "unassigned", "updated_at": now()}})
    await audit(admin, "locality.verify", loc_id, {"source": body.source})
    return clean(await db.localities.find_one({"id": loc_id}, {"_id": 0, "search_keys": 0}))


@api.post("/admin/localities/{loc_id}/deactivate")
async def admin_deactivate(loc_id: str, admin: dict = Depends(admin_user)):
    r = await db.localities.update_one({"id": loc_id}, {"$set": {"is_active": False, "updated_at": now()}})
    if not r.matched_count:
        raise HTTPException(404, "Locality not found")
    await audit(admin, "locality.deactivate", loc_id, {})
    return clean(await db.localities.find_one({"id": loc_id}, {"_id": 0, "search_keys": 0}))


@api.post("/admin/localities/{loc_id}/activate")
async def admin_activate(loc_id: str, admin: dict = Depends(admin_user)):
    loc = await db.localities.find_one({"id": loc_id}, {"_id": 0})
    if not loc:
        raise HTTPException(404, "Locality not found")
    if loc.get("merged_into"):
        raise HTTPException(400, "Merged localities cannot be reactivated")
    await check_key_conflicts(loc["city_id"], loc["search_keys"], exclude_id=loc_id)
    await db.localities.update_one({"id": loc_id}, {"$set": {"is_active": True, "updated_at": now()}})
    await audit(admin, "locality.activate", loc_id, {})
    return clean(await db.localities.find_one({"id": loc_id}, {"_id": 0, "search_keys": 0}))


@api.post("/admin/localities/merge")
async def admin_merge(body: MergeIn, admin: dict = Depends(admin_user)):
    if body.source_id == body.target_id:
        raise HTTPException(400, "Cannot merge a locality into itself")
    src = await db.localities.find_one({"id": body.source_id, "is_active": True}, {"_id": 0})
    tgt = await db.localities.find_one({"id": body.target_id, "is_active": True}, {"_id": 0})
    if not src or not tgt:
        raise HTTPException(404, "Active locality not found")
    moved = await db.properties.update_many({"locality_id": src["id"]}, {"$set": {"locality_id": tgt["id"]}})
    if tgt.get("parent_id") == src["id"]:
        await db.localities.update_one({"id": tgt["id"]}, {"$set": {"parent_id": src.get("parent_id")}})
    await db.localities.update_many({"parent_id": src["id"], "id": {"$ne": tgt["id"]}}, {"$set": {"parent_id": tgt["id"]}})
    aliases = sorted(set((tgt.get("aliases") or []) + [src["name_en"]] + (src.get("aliases") or [])))
    keys = sorted(set(tgt["search_keys"]) | set(src["search_keys"]))
    await db.localities.update_one({"id": src["id"]}, {"$set": {"is_active": False, "merged_into": tgt["id"], "search_keys": [], "updated_at": now()}})
    await db.localities.update_one({"id": tgt["id"]}, {"$set": {"aliases": aliases, "search_keys": keys, "updated_at": now()}})
    await audit(admin, "locality.merge", tgt["id"], {"source": src["id"], "listings_moved": moved.modified_count})
    return {"merged": True, "listings_moved": moved.modified_count, "target": clean(await db.localities.find_one({"id": tgt["id"]}, {"_id": 0, "search_keys": 0}))}


@api.get("/admin/seed-report")
async def admin_seed_report(admin: dict = Depends(admin_user)):
    rep = await db.seed_reports.find_one({}, {"_id": 0}, sort=[("ran_at", -1)])
    return clean(rep) or {}


@api.get("/")
async def root():
    return {"app": "LANDVILLA", "status": "ok"}


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


async def seed_test_sessions():
    """DEV ONLY: deterministic test sessions so automated tests can call authed endpoints."""
    for uid, email, role, token in [("user_testbuyer01", "buyer.test@landvilla.dev", "buyer", "test_session_buyer_landvilla"),
                                    ("user_testadmin01", "admin.test@landvilla.dev", "admin", "test_session_admin_landvilla")]:
        await db.users.update_one({"user_id": uid}, {"$set": {"email": email, "name": f"Test {role.title()}", "role": role, "picture": None},
                                                     "$setOnInsert": {"created_at": now()}}, upsert=True)
        await db.user_sessions.update_one({"session_token": token}, {"$set": {"user_id": uid, "expires_at": now() + timedelta(days=30), "created_at": now()}}, upsert=True)


@app.on_event("startup")
async def startup():
    rep = await seed_all(db, include_demo=SEED_DEMO)
    logger.info("Seed report: inserted=%s skipped=%s unresolved=%s", rep["inserted"], rep["skipped_duplicates"], rep["unresolved_localities"])
    if SEED_TEST_SESSIONS:
        await seed_test_sessions()


@app.on_event("shutdown")
async def shutdown():
    client.close()
