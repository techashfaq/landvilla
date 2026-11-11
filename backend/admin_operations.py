"""Authorized operational APIs. No payment settlement or destructive database tooling."""
import os
import re
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
import server
import marketplace

router = APIRouter(prefix="/api/admin")


def search(q, fields):
    return {"$or": [{key: {"$regex": re.escape(q), "$options": "i"}} for key in fields]} if q else {}


async def page_of(collection, flt, page, limit, projection=None):
    docs = await collection.find(flt, projection or {"_id": 0}).sort([("created_at", -1), ("_id", 1)]).skip((page - 1) * limit).limit(limit).to_list(limit)
    return {"items": [server.clean(d) for d in docs], "total": await collection.count_documents(flt), "page": page, "limit": limit}


@router.get("/users")
async def users(q: str = Query("", max_length=100), status: Literal["", "active", "suspended", "deleted"] = "", page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), admin: dict = Depends(server.admin_user)):
    flt = search(q, ("user_id", "name", "email", "phone"))
    if status:
        flt = {"$and": [flt, {"$or": [{"suspended": True}, {"account_status": "suspended"}]} if status == "suspended" else {"suspended": {"$ne": True}, "account_status": {"$nin": ["deleted", "suspended"]}} if status == "active" else {"account_status": "deleted"}]}
    result = await page_of(server.db.users, flt, page, limit, {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1, "account_status": 1, "suspended": 1, "created_at": 1})
    for u in result["items"]:
        u["status"] = "suspended" if u.get("suspended") else u.get("account_status", "active")
        u["listing_count"] = await server.db.properties.count_documents({"owner_user_id": u["user_id"], "listing_status": {"$ne": "deleted"}})
        u["enquiry_count"] = await server.db.enquiries.count_documents({"user_id": u["user_id"]})
    return result


class Reason(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    note: str = Field(min_length=5, max_length=1000)


@router.post("/users/{user_id}/{action}")
async def user_status(user_id: str, action: Literal["suspend", "reactivate"], body: Reason, admin: dict = Depends(server.admin_user)):
    u = await server.db.users.find_one({"user_id": user_id})
    if not u:
        raise HTTPException(404, "Account not found")
    if user_id == admin["user_id"] or u.get("role") == "admin" or u.get("account_status") in ("deleted", "deletion_pending"):
        raise HTTPException(403, "This account cannot be changed here")
    suspended = action == "suspend"
    result = await server.db.users.update_one({"user_id": user_id, "role": {"$ne": "admin"}, "account_status": {"$nin": ["deleted", "deletion_pending"]}}, {"$set": {"suspended": suspended, "account_status": "suspended" if suspended else "active", "updated_at": server.now()}})
    if not result.matched_count:
        raise HTTPException(409, "Account changed. Refresh before retrying")
    await server.db.user_sessions.delete_many({"user_id": user_id})
    if suspended:
        await server.db.properties.update_many({"owner_user_id": user_id, "listing_status": "active"}, {"$set": {"listing_status": "suspended", "updated_at": server.now()}, "$push": {"moderation_history": {"status": "suspended", "by": admin["user_id"], "at": server.now(), "note": body.note}}})
    await marketplace.audit(admin, "user." + action, user_id, {"note": body.note})
    return {"id": user_id, "status": "suspended" if suspended else "active"}


@router.get("/enquiries")
async def enquiries(q: str = Query("", max_length=100), status: Literal["", "new", "contacted", "follow_up", "closed"] = "", page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), admin: dict = Depends(server.admin_user)):
    flt = search(q, ("id", "property_id", "name", "lister_user_id"))
    if status: flt["status"] = status
    result = await page_of(server.db.enquiries, flt, page, limit, {"_id": 0, "id": 1, "property_id": 1, "name": 1, "intent": 1, "status": 1, "message": 1, "created_at": 1, "lister_user_id": 1})
    return result


class LeadDecision(Reason):
    status: Literal["new", "contacted", "follow_up", "closed"]


@router.post("/enquiries/{lead_id}/status")
async def lead_status(lead_id: str, body: LeadDecision, admin: dict = Depends(server.admin_user)):
    result = await server.db.enquiries.update_one({"id": lead_id}, {"$set": {"status": body.status, "updated_at": server.now()}})
    if not result.matched_count: raise HTTPException(404, "Enquiry not found")
    await marketplace.audit(admin, "enquiry.status", lead_id, {"note": body.note, "status": body.status})
    return {"id": lead_id, "status": body.status}


@router.get("/audit")
async def audit(q: str = Query("", max_length=100), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), admin: dict = Depends(server.admin_user)):
    result = await page_of(server.db.audit_logs, search(q, ("actor", "action", "target", "details.note")), page, limit)
    result["items"] = [{k: d.get(k) for k in ("id", "actor", "action", "target", "created_at")} | {"note": (d.get("details") or {}).get("note", "")} for d in result["items"]]
    return result


@router.get("/staff")
async def staff(q: str = Query("", max_length=100), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), admin: dict = Depends(server.admin_user)):
    flt = {"role": "admin", **search(q, ("user_id", "name", "email"))}
    return await page_of(server.db.users, flt, page, limit, {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1, "admin_permissions": 1})


class StaffPermissions(Reason):
    permissions: list[Literal["listings", "brokers", "users", "enquiries", "featured-plans", "payments", "localities", "cms", "audit", "reports", "zones", "cities"]] = Field(max_length=12)
    enabled: bool = True


@router.post("/staff/{user_id}/permissions")
async def staff_permissions(user_id: str, body: StaffPermissions, admin: dict = Depends(server.admin_user)):
    managers = {v.strip() for v in os.getenv("STAFF_MANAGER_IDS", "").split(",") if v.strip()}
    if admin["user_id"] not in managers or user_id in managers or user_id == admin["user_id"]:
        raise HTTPException(403, "Staff provisioning requires a designated independent staff manager")
    u = await server.db.users.find_one({"user_id": user_id, "suspended": {"$ne": True}, "account_status": {"$nin": ["deleted", "suspended", "deletion_pending"]}})
    if not u: raise HTTPException(404, "Active account not found")
    await server.db.users.update_one({"user_id": user_id}, {"$set": {"role": "admin" if body.enabled else "buyer", "admin_permissions": list(dict.fromkeys(body.permissions)) if body.enabled else []}})
    await server.db.user_sessions.delete_many({"user_id": user_id})
    await marketplace.audit(admin, "staff.permissions", user_id, {"note": body.note, "permissions": body.permissions, "enabled": body.enabled})
    return {"id": user_id, "saved": True}

class ContentIn(Reason):
    kind: Literal["home-banner", "faq", "support"]
    title: str = Field(min_length=3, max_length=160)
    body: str = Field(min_length=3, max_length=4000)
    status: Literal["draft", "published"] = "draft"
    link: Literal["", "/properties", "/buy", "/rent", "/contact", "/faq"] = ""


@router.get("/cms")
async def cms(q: str = Query("", max_length=100), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), admin: dict = Depends(server.admin_user)):
    return await page_of(server.db.cms_content, search(q, ("title", "kind", "body")), page, limit)


@router.post("/cms")
async def create_content(body: ContentIn, admin: dict = Depends(server.admin_user)):
    doc = {"id": marketplace.uid("content"), **body.model_dump(exclude={"note"}), "created_at": server.now(), "updated_at": server.now()}
    await server.db.cms_content.insert_one(doc)
    await marketplace.audit(admin, "content.create", doc["id"], {"note": body.note, "status": body.status})
    return {"id": doc["id"], "saved": True}


@router.put("/cms/{content_id}")
async def update_content(content_id: str, body: ContentIn, admin: dict = Depends(server.admin_user)):
    result = await server.db.cms_content.update_one({"id": content_id}, {"$set": {**body.model_dump(exclude={"note"}), "updated_at": server.now()}})
    if not result.matched_count: raise HTTPException(404, "Content not found")
    await marketplace.audit(admin, "content.update", content_id, {"note": body.note, "status": body.status})
    return {"id": content_id, "saved": True}


class GeographyIn(Reason):
    name_en: str = Field(min_length=2, max_length=80)
    name_hi: str = Field(min_length=1, max_length=80)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    is_active: bool = False


@router.get("/cities")
@router.get("/zones")
async def geography(request: server.Request, q: str = Query("", max_length=100), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), admin: dict = Depends(server.admin_user)):
    collection = server.db.cities if request.url.path.endswith("cities") else server.db.zones
    return await page_of(collection, search(q, ("name_en", "name_hi", "slug")), page, limit)


@router.post("/cities")
@router.post("/zones")
async def create_geography(request: server.Request, body: GeographyIn, admin: dict = Depends(server.admin_user)):
    is_city = request.url.path.endswith("cities")
    collection = server.db.cities if is_city else server.db.zones
    if is_city and body.is_active:
        raise HTTPException(400, "New cities must remain inactive until launch support is configured")
    if await collection.find_one({"slug": body.slug}): raise HTTPException(409, "Slug already exists")
    doc = {"id": marketplace.uid("city" if is_city else "zone"), **body.model_dump(exclude={"note"}), "created_at": server.now()}
    if not is_city:
        city = await server.db.cities.find_one({"slug": "ujjain"})
        if not city: raise HTTPException(409, "Ujjain must be configured first")
        doc["city_id"] = city["id"]
    await collection.insert_one(doc)
    await marketplace.audit(admin, "city.create" if is_city else "zone.create", doc["id"], {"note": body.note})
    return {"id": doc["id"], "saved": True}

@router.put("/zones/{zone_id}")
async def update_zone(zone_id: str, body: GeographyIn, admin: dict = Depends(server.admin_user)):
    zone = await server.db.zones.find_one({"id": zone_id})
    if not zone: raise HTTPException(404, "Zone not found")
    if body.slug != zone.get("slug"):
        raise HTTPException(400, "Existing slugs are preserved to protect public links")
    result = await server.db.zones.update_one({"id": zone_id}, {"$set": {**body.model_dump(exclude={"note"}), "updated_at": server.now()}})
    if not result.matched_count: raise HTTPException(409, "Zone changed")
    await marketplace.audit(admin, "zone.update", zone_id, {"note": body.note})
    return {"id": zone_id, "saved": True}

@router.get("/enquiries/{lead_id}")
async def enquiry_detail(lead_id: str, admin: dict = Depends(server.admin_user)):
    lead = await server.db.enquiries.find_one({"id": lead_id})
    if not lead: raise HTTPException(404, "Enquiry not found")
    prop = await server.db.properties.find_one({"id": lead.get("property_id")})
    await marketplace.log_contact_access(admin, lead)
    await marketplace.audit(admin, "enquiry.view", lead_id, {})
    return {"id": lead_id, "name": lead.get("name"), "status": lead.get("status"), "intent": lead.get("intent"), "message": lead.get("message"), "phone": lead.get("phone") if lead.get("share_phone_consent") else None, "phone_masked": marketplace.mask_phone(lead.get("phone", "")), "property_title": (prop or {}).get("title_en"), "property_id": lead.get("property_id"), "lister_user_id": lead.get("lister_user_id"), "created_at": server.clean({"value": lead.get("created_at")})["value"]}
