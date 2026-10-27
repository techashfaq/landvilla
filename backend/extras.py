"""LANDVILLA extras: legal pages, account deletion, report/block, commission agreements, locality SEO.
Imported at the bottom of server.py, after the db/auth helpers exist.
"""
import html
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from server import admin_user, clean, current_user, db, now

router = APIRouter(prefix="/api")
E = html.escape
REAUTH_SECONDS = 30 * 60  # account deletion needs a sign-in within the last 30 minutes
MAX_REPORTS_PER_DAY = 10


async def check_report_rate(user_id: str):
    since = now() - timedelta(days=1)
    if await db.abuse_reports.count_documents({"reporter_id": user_id, "created_at": {"$gte": since}}) >= MAX_REPORTS_PER_DAY:
        raise HTTPException(429, "Too many reports today. Please try again tomorrow.")


def uid(p: str) -> str:
    return f"{p}_{uuid.uuid4().hex[:12]}"


async def audit(actor: str, action: str, target: str, details: dict):
    await db.audit_logs.insert_one({"id": uid("aud"), "actor": actor, "action": action, "target": target, "details": details, "created_at": now()})


def base_url(request: Request) -> str:
    env = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if env:
        return env
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    return f"https://{host}"


# ------------------------------------------------------------------ legal documents (admin-configurable)
LEGAL_DEFAULTS = {
    "privacy": {"title": "Privacy Policy", "version": "draft-2026-10", "body": """DRAFT – pending review by a qualified Indian lawyer before launch.

1. Who we are. LANDVILLA ("we") runs a property marketplace starting in Ujjain, Madhya Pradesh. Contact: [support email to be configured by admin].

2. What we collect. Google sign-in data (name, email, profile photo); enquiry details (name, mobile number, message, intent); in-app messages; property listings and photos you post; broker verification details and identity documents; payment records for Featured listings (processed by Razorpay – we do not store card or UPI details); technical logs needed to run the service.

3. Why we use it. To run accounts, show listings, deliver enquiries to the right owner or broker, moderate content, prevent fraud and abuse, process payments, and meet legal obligations.

4. Phone number privacy. Your mobile number is hidden from owners and brokers unless you tick the consent box for that specific enquiry. Access to shared numbers is logged.

5. Sharing. With the owner/broker you enquire with (as described above); with service providers who host our servers, files and payments (e.g. Razorpay); with authorities when required by law. We do not sell personal data.

6. Retention. We keep data while your account is active. When you delete your account we delete or anonymise personal data, except records we must keep by law (for example payment and invoice records for tax purposes), which are retained only as long as required.

7. Your rights. You can access, correct or delete your data, and withdraw consent, under the Digital Personal Data Protection Act, 2023. Delete your account in the app (Profile → Delete account) or via the public deletion request page.

8. Security. Data is encrypted in transit. Identity documents are stored privately and visible only to authorised LANDVILLA administrators; such access is logged.

9. Changes. We will show the updated version and date here."""},
    "terms": {"title": "Terms & Conditions", "version": "draft-2026-10", "body": """DRAFT – pending review by a qualified Indian lawyer before launch.

1. The service. LANDVILLA lets people find, list and enquire about properties. We are a platform; we are not a party to any property transaction unless a separate written agreement says so.

2. No legal verification. Listing review (moderation) checks quality and obvious problems only. It is NOT a guarantee of title, ownership, approvals, RERA registration or legal status. Buyers and tenants must do their own legal due diligence.

3. Listers. Owners declare they own or are authorised to list the property. Brokers must pass identity verification and admin approval before posting as a broker. False listings, duplicate spam or misuse can lead to removal and account suspension.

4. Featured listings. Paid Featured placement moves a live listing to the top of its area's results for the purchased period. Featuring starts only after payment is verified and ends automatically. Fees are non-refundable once featuring has started, except where required by law.

5. Commission. LANDVILLA charges a transaction commission ONLY where it provides an agreed transaction or brokerage service AND the payer has accepted a separate written commission agreement beforehand. Reporting a completed deal alone never makes commission payable.

6. Conduct. Do not harass users, share others' personal data, post illegal or misleading content, or bypass safety features. Use Report and Block to flag abuse; we review reports and may remove content or accounts.

7. Liability. To the extent permitted by law, LANDVILLA is not liable for losses arising from dealings between users.

8. Disputes and governing law. Laws of India apply. Complaints: [grievance officer contact to be configured by admin]."""},
}


async def legal_doc(doc: str) -> dict:
    if doc not in LEGAL_DEFAULTS:
        raise HTTPException(404, "Not found")
    d = await db.legal_documents.find_one({"doc": doc}, {"_id": 0})
    return clean(d) if d else {"doc": doc, **LEGAL_DEFAULTS[doc], "updated_at": None}


@router.get("/legal/{doc}.json")
async def legal_json(doc: str):
    return await legal_doc(doc)


def page(title: str, body_html: str, desc: str = "", canonical: str = "", robots: str = "index,follow", extra_head: str = "") -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{E(title)}</title><meta name="description" content="{E(desc)}"/><meta name="robots" content="{robots}"/>
{f'<link rel="canonical" href="{E(canonical)}"/>' if canonical else ''}
<meta property="og:title" content="{E(title)}"/><meta property="og:description" content="{E(desc)}"/>{f'<meta property="og:url" content="{E(canonical)}"/>' if canonical else ''}
{extra_head}
<style>body{{font-family:system-ui,-apple-system,"Noto Sans Devanagari",sans-serif;max-width:760px;margin:0 auto;padding:16px;color:#1C1917;line-height:1.55}}
h1{{color:#B84A1E}}a{{color:#B84A1E}}.card{{border:1px solid #E7E5E4;border-radius:12px;padding:12px;margin:8px 0}}.muted{{color:#78716C;font-size:14px}}
pre{{white-space:pre-wrap;font-family:inherit}}input,textarea,button{{font:inherit;padding:10px;border-radius:8px;border:1px solid #D6D3D1;width:100%;box-sizing:border-box;margin:6px 0}}button{{background:#B84A1E;color:#fff;border:0}}</style>
</head><body><header><b>LANDVILLA</b></header>{body_html}<footer class="muted"><hr/><a href="/api/legal/privacy">Privacy</a> · <a href="/api/legal/terms">Terms</a> · <a href="/api/legal/delete-account">Delete account</a></footer></body></html>""")


@router.get("/legal/delete-account", response_class=HTMLResponse)
async def delete_account_page():
    return page("Delete your LANDVILLA account", """<h1>Delete your account</h1>
<p>In the app: <b>Profile → Delete account</b>. This deletes your account immediately.</p>
<p>Can't use the app? Submit a request below with the Google email you sign in with. We verify ownership by contacting that email before deleting. Personal data is deleted or anonymised; payment/invoice records required by tax law are retained only as long as legally required.</p>
<form method="post" action="/api/legal/delete-account"><input name="email" type="email" required placeholder="Your Google account email"/>
<textarea name="reason" rows="3" placeholder="Reason (optional)"></textarea><button type="submit">Request deletion</button></form>""", "Request deletion of your LANDVILLA account and personal data.")


@router.post("/legal/delete-account", response_class=HTMLResponse)
async def delete_account_request(request: Request, email: str = Form(...), reason: str = Form("")):
    email = email.strip().lower()[:200]
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(400, "Enter a valid email")
    day = now() - timedelta(days=1)
    # Client IP as reported by the proxy (spoofable, so it is a soft limit; the per-email limit is the hard guard).
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[0].strip()
    if await db.deletion_requests.count_documents({"email": email, "created_at": {"$gte": day}}) >= 2 or \
            await db.deletion_requests.count_documents({"ip": ip, "created_at": {"$gte": now() - timedelta(hours=1)}}) >= 5:
        return page("Request already received", "<h1>Request already received</h1><p>We already have a recent request for this email and will contact you.</p>", robots="noindex")
    await db.deletion_requests.insert_one({"id": uid("delreq"), "email": email, "reason": reason[:500], "ip": ip, "status": "open", "created_at": now()})
    return page("Request received", "<h1>Request received</h1><p>We will verify the request by email and complete deletion within 30 days.</p>")


@router.get("/legal/{doc}", response_class=HTMLResponse)
async def legal_page(doc: str, request: Request):
    d = await legal_doc(doc)
    return page(f"{d['title']} – LANDVILLA", f"<h1>{E(d['title'])}</h1><p class='muted'>Version {E(d['version'])}</p><pre>{E(d['body'])}</pre>",
                d["title"], f"{base_url(request)}/api/legal/{doc}")


class LegalIn(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    version: str = Field(min_length=1, max_length=40)
    body: str = Field(min_length=50, max_length=50000)


@router.put("/admin/legal/{doc}")
async def admin_update_legal(doc: str, body: LegalIn, admin: dict = Depends(admin_user)):
    if doc not in LEGAL_DEFAULTS:
        raise HTTPException(404, "Not found")
    await db.legal_documents.update_one({"doc": doc}, {"$set": {**body.model_dump(), "doc": doc, "updated_at": now(), "updated_by": admin["user_id"]}}, upsert=True)
    await audit(admin["user_id"], "legal.update", doc, {"version": body.version})
    return await legal_doc(doc)


# ------------------------------------------------------------------ account deletion
class DeleteIn(BaseModel):
    confirm: str


@router.post("/account/delete")
async def delete_account(body: DeleteIn, request: Request, user: dict = Depends(current_user)):
    if body.confirm.strip().upper() != "DELETE":
        raise HTTPException(400, "Type DELETE to confirm")
    created = user.get("_session_created_at")
    if not created or (now() - created).total_seconds() > REAUTH_SECONDS:
        raise HTTPException(403, "reauth_required: please sign in again to confirm it's you, then delete your account")
    u = user["user_id"]
    # Files (photos & private documents) – stop serving and mark for storage purge.
    await db.files.update_many({"owner_id": u}, {"$set": {"is_deleted": True, "deleted_reason": "account_deleted", "deleted_at": now()}})
    # Listings – remove from public view and strip lister identity.
    await db.properties.update_many({"owner_user_id": u}, {"$set": {"listing_status": "removed", "featured": False, "posted_by_name": "Deleted user",
                                                                     "owner_user_id": None, "deleted_owner": True, "updated_at": now()}})
    # Enquiries as buyer – anonymise personal data, keep minimal record for the lister's history.
    await db.enquiries.update_many({"user_id": u}, {"$set": {"user_id": None, "name": "Deleted user", "phone": "", "share_phone_consent": False,
                                                              "message": "", "messages": [], "buyer_deleted": True}})
    # Leads as lister – detach.
    await db.enquiries.update_many({"lister_user_id": u}, {"$set": {"lister_user_id": None, "notes": []}})
    await db.broker_profiles.delete_one({"user_id": u})
    await db.saved.delete_many({"user_id": u})
    await db.blocks.delete_many({"$or": [{"blocker_id": u}, {"blocked_id": u}]})
    await db.contact_access_logs.update_many({"$or": [{"viewer_id": u}, {"buyer_user_id": u}]}, {"$set": {"viewer_id": "deleted", "buyer_user_id": "deleted"}})
    # Payments & commission records are retained for tax/accounting law, with the user reference pseudonymised.
    tomb = f"deleted_{uuid.uuid4().hex[:8]}"
    await db.payment_orders.update_many({"user_id": u}, {"$set": {"user_id": tomb, "retained_reason": "tax/accounting retention"}})
    await db.user_sessions.delete_many({"user_id": u})
    await db.users.delete_one({"user_id": u})
    await audit(tomb, "account.delete", tomb, {"retained": ["payment_orders"]})
    return {"deleted": True}


# ------------------------------------------------------------------ report & block
class ReportIn(BaseModel):
    reason: Literal["fake_listing", "wrong_info", "spam", "abuse", "fraud", "other"]
    note: Optional[str] = Field(default="", max_length=500)


@router.post("/properties/{prop_id}/report")
async def report_property(prop_id: str, body: ReportIn, user: dict = Depends(current_user)):
    if not await db.properties.find_one({"id": prop_id}):
        raise HTTPException(404, "Property not found")
    await check_report_rate(user["user_id"])
    if await db.abuse_reports.find_one({"target_type": "property", "target_id": prop_id, "reporter_id": user["user_id"], "status": "open"}):
        raise HTTPException(409, "You already reported this listing")
    await db.abuse_reports.insert_one({"id": uid("abuse"), "target_type": "property", "target_id": prop_id, "reporter_id": user["user_id"],
                                       "reason": body.reason, "note": (body.note or "").strip(), "status": "open", "created_at": now()})
    return {"reported": True}


@router.post("/enquiries/{enq_id}/report-user")
async def report_enquiry_user(enq_id: str, body: ReportIn, user: dict = Depends(current_user)):
    e = await db.enquiries.find_one({"id": enq_id}, {"_id": 0})
    if not e or user["user_id"] not in (e.get("user_id"), e.get("lister_user_id")):
        raise HTTPException(404, "Enquiry not found")
    other = e.get("lister_user_id") if user["user_id"] == e.get("user_id") else e.get("user_id")
    await check_report_rate(user["user_id"])
    await db.abuse_reports.insert_one({"id": uid("abuse"), "target_type": "enquiry", "target_id": enq_id, "reported_user_id": other,
                                       "reporter_id": user["user_id"], "reason": body.reason, "note": (body.note or "").strip(), "status": "open", "created_at": now()})
    return {"reported": True}


async def is_blocked(a: Optional[str], b: Optional[str]) -> bool:
    if not a or not b:
        return False
    return bool(await db.blocks.find_one({"$or": [{"blocker_id": a, "blocked_id": b}, {"blocker_id": b, "blocked_id": a}]}))


@router.post("/enquiries/{enq_id}/block")
async def block_from_enquiry(enq_id: str, user: dict = Depends(current_user)):
    e = await db.enquiries.find_one({"id": enq_id}, {"_id": 0})
    if not e or user["user_id"] not in (e.get("user_id"), e.get("lister_user_id")):
        raise HTTPException(404, "Enquiry not found")
    other = e.get("lister_user_id") if user["user_id"] == e.get("user_id") else e.get("user_id")
    if not other:
        raise HTTPException(400, "Nobody to block on this enquiry")
    await db.blocks.update_one({"blocker_id": user["user_id"], "blocked_id": other}, {"$setOnInsert": {"created_at": now(), "enquiry_id": enq_id}}, upsert=True)
    await audit(user["user_id"], "user.block", other, {"enquiry_id": enq_id})
    return {"blocked": True}


@router.delete("/enquiries/{enq_id}/block")
async def unblock_from_enquiry(enq_id: str, user: dict = Depends(current_user)):
    e = await db.enquiries.find_one({"id": enq_id}, {"_id": 0})
    if not e:
        raise HTTPException(404, "Enquiry not found")
    other = e.get("lister_user_id") if user["user_id"] == e.get("user_id") else e.get("user_id")
    await db.blocks.delete_one({"blocker_id": user["user_id"], "blocked_id": other})
    return {"blocked": False}


@router.get("/admin/reports")
async def admin_reports(status: str = "open", admin: dict = Depends(admin_user)):
    docs = await db.abuse_reports.find({"status": status}, {"_id": 0}).sort("created_at", -1).to_list(200)
    out = []
    for d in docs:
        x = clean(d)
        if d.get("target_type") == "property":
            p = await db.properties.find_one({"id": d["target_id"]}, {"_id": 0, "title_en": 1, "listing_status": 1})
            x["target_label"] = (p or {}).get("title_en", "(deleted)")
            x["target_status"] = (p or {}).get("listing_status")
        else:
            x["target_label"] = f"Enquiry {d.get('target_id') or d.get('enquiry_id')}"
        out.append(x)
    deletion = await db.deletion_requests.find({"status": "open"}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"items": out, "deletion_requests": [clean(r) for r in deletion]}


class ResolveIn(BaseModel):
    action: Literal["dismiss", "remove_listing", "suspend_user"]
    note: str = Field(min_length=3, max_length=500)


class DelReqIn(BaseModel):
    status: Literal["completed", "rejected"]
    note: str = Field(min_length=3, max_length=500)


@router.post("/admin/deletion-requests/{req_id}")
async def admin_close_deletion_request(req_id: str, body: DelReqIn, admin: dict = Depends(admin_user)):
    r = await db.deletion_requests.update_one({"id": req_id, "status": "open"}, {"$set": {"status": body.status, "resolution_note": body.note,
                                              "resolved_by": admin["user_id"], "resolved_at": now()}})
    if not r.matched_count:
        raise HTTPException(404, "Open request not found")
    await audit(admin["user_id"], f"deletion_request.{body.status}", req_id, {"note": body.note})
    return {"status": body.status}


@router.post("/admin/reports/{rep_id}/resolve")
async def admin_resolve_report(rep_id: str, body: ResolveIn, admin: dict = Depends(admin_user)):
    r = await db.abuse_reports.find_one({"id": rep_id, "status": "open"}, {"_id": 0})
    if not r:
        raise HTTPException(404, "Open report not found")
    if body.action == "remove_listing":
        if r.get("target_type") != "property":
            raise HTTPException(400, "Not a listing report")
        await db.properties.update_one({"id": r["target_id"]}, {"$set": {"listing_status": "rejected", "featured": False,
                                        "moderation": {"status": "rejected", "note": f"Removed after report: {body.note}", "by": admin["user_id"], "at": now()}}})
    elif body.action == "suspend_user":
        target = r.get("reported_user_id")
        if not target:
            raise HTTPException(400, "No user on this report")
        await db.users.update_one({"user_id": target}, {"$set": {"suspended": True, "suspended_at": now()}})
        await db.user_sessions.delete_many({"user_id": target})
    await db.abuse_reports.update_one({"id": rep_id}, {"$set": {"status": "resolved", "resolution": body.action, "resolution_note": body.note,
                                                                "resolved_by": admin["user_id"], "resolved_at": now()}})
    await audit(admin["user_id"], f"report.{body.action}", rep_id, {"note": body.note})
    return {"resolved": True}


# ------------------------------------------------------------------ commission agreements (admin only)
COMMISSION_STATES = ["draft", "agreement_accepted", "deal_reported", "approved_payable", "invoiced", "paid", "disputed", "waived", "cancelled"]
TRANSITIONS = {
    "draft": ["agreement_accepted", "cancelled"],
    "agreement_accepted": ["deal_reported", "cancelled"],
    "deal_reported": ["approved_payable", "disputed", "waived", "cancelled"],
    "approved_payable": ["invoiced", "disputed", "waived"],
    "invoiced": ["paid", "disputed", "waived"],
    "disputed": ["approved_payable", "waived", "cancelled"],
    "paid": [], "waived": [], "cancelled": [],
}


async def commission_settings() -> dict:
    s = await db.app_settings.find_one({"key": "commission"}, {"_id": 0}) or {}
    return {"default_rate_percent": s.get("default_rate_percent", 1.0), "auto_charge": False,
            "requires_written_agreement": True, "legal_review_complete": bool(s.get("legal_review_complete")),
            "collection_enabled": bool(s.get("collection_enabled")) and bool(s.get("legal_review_complete")), "updated_at": clean({"x": s.get("updated_at")})["x"]}


class CommissionSettingsIn(BaseModel):
    default_rate_percent: float = Field(ge=0, le=10)
    legal_review_complete: bool = False
    collection_enabled: bool = False


@router.get("/admin/commission/settings")
async def get_commission_settings(admin: dict = Depends(admin_user)):
    return await commission_settings()


@router.put("/admin/commission/settings")
async def put_commission_settings(body: CommissionSettingsIn, admin: dict = Depends(admin_user)):
    if body.collection_enabled and not body.legal_review_complete:
        raise HTTPException(400, "Collection can only be enabled after legal review is marked complete")
    await db.app_settings.update_one({"key": "commission"}, {"$set": {**body.model_dump(), "updated_at": now(), "updated_by": admin["user_id"]}}, upsert=True)
    await audit(admin["user_id"], "commission.settings", "commission", body.model_dump())
    return await commission_settings()


class AgreementIn(BaseModel):
    property_id: Optional[str] = None
    property_description: str = Field(min_length=5, max_length=300)
    payer_type: Literal["owner", "buyer", "tenant", "other"]
    payer_name: str = Field(min_length=2, max_length=120)
    rate_percent: float = Field(ge=0, le=10)
    calculation_method: str = Field(min_length=3, max_length=300)
    due_terms: str = Field(min_length=3, max_length=300)
    taxes_note: str = Field(min_length=3, max_length=300)
    cancellation_terms: str = Field(min_length=3, max_length=500)
    dispute_process: str = Field(min_length=3, max_length=500)
    service_description: str = Field(min_length=5, max_length=500)


def amount_for(c: dict) -> Optional[float]:
    if c.get("agreement_accepted_at") and c.get("deal_value"):
        return round(c["deal_value"] * c["rate_percent"] / 100, 2)
    return None


def cview(c: dict) -> dict:
    x = clean(c)
    x["audit"] = [clean(a) for a in c.get("audit", [])]
    x["invoices"] = [clean(i) for i in c.get("invoices", [])]
    x["payments"] = [clean(p) for p in c.get("payments", [])]
    x["commission_amount"] = amount_for(c)
    x["allowed_next"] = TRANSITIONS.get(c["status"], [])
    return x


def entry(admin: dict, action: str, **details) -> dict:
    return {"at": now(), "by": admin["user_id"], "action": action, "details": details}


@router.get("/admin/commissions")
async def list_commissions(admin: dict = Depends(admin_user)):
    docs = await db.commission_agreements.find({}, {"_id": 0}).sort("created_at", -1).to_list(300)
    return {"items": [cview(d) for d in docs], "settings": await commission_settings()}


@router.post("/admin/commissions")
async def create_commission(body: AgreementIn, admin: dict = Depends(admin_user)):
    if body.property_id and not await db.properties.find_one({"id": body.property_id}):
        raise HTTPException(400, "Unknown property")
    doc = {"id": uid("comm"), **body.model_dump(), "status": "draft", "deal_value": None, "deal_reported_at": None, "deal_report_source": None,
           "agreement_accepted_at": None, "acceptance_evidence": None, "invoices": [], "payments": [], "created_at": now(), "updated_at": now(),
           "audit": [entry(admin, "created", rate_percent=body.rate_percent, payer=body.payer_name)]}
    await db.commission_agreements.insert_one(doc)
    return cview(doc)


class TransitionIn(BaseModel):
    status: str
    note: str = Field(min_length=3, max_length=1000)
    acceptance_evidence: Optional[str] = Field(default=None, max_length=500)
    deal_value: Optional[float] = Field(default=None, gt=0)
    deal_report_source: Optional[str] = Field(default=None, max_length=200)


@router.post("/admin/commissions/{cid}/status")
async def transition_commission(cid: str, body: TransitionIn, admin: dict = Depends(admin_user)):
    c = await db.commission_agreements.find_one({"id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Agreement not found")
    if body.status not in TRANSITIONS.get(c["status"], []):
        raise HTTPException(400, f"Cannot move from {c['status']} to {body.status}")
    upd = {"status": body.status, "updated_at": now()}
    if body.status == "agreement_accepted":
        if not body.acceptance_evidence or len(body.acceptance_evidence.strip()) < 5:
            raise HTTPException(400, "Record how the payer accepted the written agreement (signed copy reference, e-sign ID, date)")
        upd |= {"agreement_accepted_at": now(), "acceptance_evidence": body.acceptance_evidence.strip()}
    if body.status == "deal_reported":
        if not body.deal_value:
            raise HTTPException(400, "Declared deal value is required")
        upd |= {"deal_value": body.deal_value, "deal_reported_at": now(), "deal_report_source": (body.deal_report_source or "").strip() or "reported"}
    if body.status == "approved_payable" and not (c.get("agreement_accepted_at") and (c.get("deal_value") or body.deal_value)):
        raise HTTPException(400, "Commission is payable only with an accepted agreement and a reported deal value")
    log = entry(admin, f"status:{body.status}", note=body.note, deal_value=body.deal_value)
    await db.commission_agreements.update_one({"id": cid}, {"$set": upd, "$push": {"audit": log}})
    return cview(await db.commission_agreements.find_one({"id": cid}, {"_id": 0}))


class CorrectIn(BaseModel):
    rate_percent: Optional[float] = Field(default=None, ge=0, le=10)
    deal_value: Optional[float] = Field(default=None, gt=0)
    note: str = Field(min_length=3, max_length=1000)


@router.post("/admin/commissions/{cid}/correct")
async def correct_commission(cid: str, body: CorrectIn, admin: dict = Depends(admin_user)):
    c = await db.commission_agreements.find_one({"id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Agreement not found")
    if c["status"] in ("paid", "waived", "cancelled"):
        raise HTTPException(400, "Closed records cannot be corrected")
    upd = {k: v for k, v in {"rate_percent": body.rate_percent, "deal_value": body.deal_value}.items() if v is not None}
    if not upd:
        raise HTTPException(400, "Nothing to correct")
    log = entry(admin, "corrected", note=body.note, before={k: c.get(k) for k in upd}, after=upd)
    await db.commission_agreements.update_one({"id": cid}, {"$set": {**upd, "updated_at": now()}, "$push": {"audit": log}})
    return cview(await db.commission_agreements.find_one({"id": cid}, {"_id": 0}))


class InvoiceIn(BaseModel):
    invoice_number: str = Field(min_length=2, max_length=60)
    amount: float = Field(gt=0)
    tax_amount: float = Field(ge=0)
    note: Optional[str] = Field(default="", max_length=300)


@router.post("/admin/commissions/{cid}/invoices")
async def add_invoice(cid: str, body: InvoiceIn, admin: dict = Depends(admin_user)):
    c = await db.commission_agreements.find_one({"id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Agreement not found")
    if c["status"] not in ("approved_payable", "invoiced"):
        raise HTTPException(400, "Invoices can only be raised on approved payable commissions")
    inv = {"id": uid("inv"), **body.model_dump(), "issued_at": now(), "issued_by": admin["user_id"]}
    await db.commission_agreements.update_one({"id": cid}, {"$push": {"invoices": inv, "audit": entry(admin, "invoice", number=body.invoice_number, amount=body.amount)},
                                                            "$set": {"status": "invoiced", "updated_at": now()}})
    return cview(await db.commission_agreements.find_one({"id": cid}, {"_id": 0}))


class PaymentRecIn(BaseModel):
    amount: float = Field(gt=0)
    method: str = Field(min_length=2, max_length=60)
    reference: str = Field(min_length=2, max_length=120)


@router.post("/admin/commissions/{cid}/payments")
async def record_payment(cid: str, body: PaymentRecIn, admin: dict = Depends(admin_user)):
    s = await commission_settings()
    if not s["collection_enabled"]:
        raise HTTPException(403, "Commission collection is disabled until legal review is complete")
    c = await db.commission_agreements.find_one({"id": cid}, {"_id": 0})
    if not c or c["status"] != "invoiced":
        raise HTTPException(400, "Payments can be recorded only against an invoiced commission")
    pay = {"id": uid("cpay"), **body.model_dump(), "recorded_at": now(), "recorded_by": admin["user_id"]}
    await db.commission_agreements.update_one({"id": cid}, {"$push": {"payments": pay, "audit": entry(admin, "payment", amount=body.amount, reference=body.reference)},
                                                            "$set": {"updated_at": now()}})
    return cview(await db.commission_agreements.find_one({"id": cid}, {"_id": 0}))


# ------------------------------------------------------------------ locality SEO pages
def inr(v: int, purpose: str) -> str:
    if purpose == "rent" or v < 100000:
        return f"₹{v:,}" + ("/month" if purpose == "rent" else "")
    return f"₹{v / 10000000:.2f} Cr" if v >= 10000000 else f"₹{v / 100000:.2f} L"


async def seo_listings(loc_id: str) -> List[dict]:
    return await db.properties.find({"locality_id": loc_id, "listing_status": "active", "is_demo": {"$ne": True}}, {"_id": 0}).sort([("featured", -1), ("created_at", -1)]).to_list(50)


async def indexable(loc: dict, n_listings: int) -> bool:
    """Avoid thin pages: index only when there are genuine live listings."""
    return loc.get("is_active") and n_listings > 0


@router.get("/l/{city}/{slug}", response_class=HTMLResponse)
async def locality_page(city: str, slug: str, request: Request):
    c = await db.cities.find_one({"slug": city, "is_active": True}, {"_id": 0})
    loc = await db.localities.find_one({"city_id": (c or {}).get("id"), "slug": slug}, {"_id": 0}) if c else None
    if not c or not loc:
        return HTMLResponse(page("Not found – LANDVILLA", "<h1>Locality not found</h1>", robots="noindex").body, status_code=404)
    base = base_url(request)
    if loc.get("merged_into"):
        tgt = await db.localities.find_one({"id": loc["merged_into"]}, {"_id": 0, "slug": 1})
        if tgt:
            return Response(status_code=301, headers={"Location": f"{base}/api/l/{city}/{tgt['slug']}"})
    props = await seo_listings(loc["id"])
    zone = await db.zones.find_one({"id": loc.get("zone_id")}, {"_id": 0}) if loc.get("zone_id") else None
    nearby = await db.localities.find({"zone_id": loc.get("zone_id"), "id": {"$ne": loc["id"]}, "is_active": True}, {"_id": 0}).to_list(20) if zone else []
    canonical = f"{base}/api/l/{city}/{slug}"
    buy = [p for p in props if p["purpose"] == "buy"]
    rent = [p for p in props if p["purpose"] == "rent"]
    title = f"Property in {loc['name_en']}, {c['name_en']} – {len(buy)} for sale, {len(rent)} for rent | LANDVILLA"
    desc = (f"{len(props)} verified-by-moderation live listings in {loc['name_en']} ({loc['name_hi']}), {c['name_en']}. "
            f"Browse flats, houses, plots and shops for sale or rent on LANDVILLA.") if props else f"Listings in {loc['name_en']}, {c['name_en']} on LANDVILLA."
    stats = ""
    for label, group in (("For sale", buy), ("For rent", rent)):
        if group:
            prices = sorted(p["price"] for p in group)
            stats += f"<li>{label}: {len(group)} listings, asking {inr(prices[0], group[0]['purpose'])} – {inr(prices[-1], group[0]['purpose'])} (live listings only, not market data)</li>"
    cards = "".join(
        f"<div class='card'><b>{E(p['title_en'])}</b><br/>{E(inr(p['price'], p['purpose']))} · {p.get('bhk') or ''}{' BHK · ' if p.get('bhk') else ''}{p.get('area_sqft')} sq.ft"
        f"{' · ⭐ Featured' if p.get('featured') else ''}<br/><span class='muted'>{E(p['type'].replace('-', ' ').title())} · {'Sale' if p['purpose'] == 'buy' else 'Rent'}</span></div>"
        for p in props)
    near = " · ".join(f"<a href='{base}/api/l/{city}/{n['slug']}'>{E(n['name_en'])}</a>" for n in nearby)
    aliases = ", ".join(E(a) for a in loc.get("aliases") or [])
    verified = loc.get("verification_status") == "verified"
    body = f"""<h1>Property in {E(loc['name_en'])}, {E(c['name_en'])}</h1><p lang="hi">{E(loc['name_hi'])}, {E(c['name_hi'])}</p>
<p>{E(loc['name_en'])} is a locality in {E(c['name_en'])}, {E(c['state_en'])}{f", in the {E(zone['name_en'])} area" if zone else ''}.{f' Also known as: {aliases}.' if aliases else ''}
{'' if verified else '<br/><span class="muted">Locality details are pending verification by our team.</span>'}</p>
{f'<h2>Live listings summary</h2><ul>{stats}</ul>' if stats else ''}
<h2>Listings in {E(loc['name_en'])}</h2>{cards or '<p>No live listings right now. Check back soon or post your property on the LANDVILLA app.</p>'}
{f'<h2>Nearby localities</h2><p>{near}</p>' if near else ''}
<p class="muted">Listings are reviewed for quality; this is not a guarantee of title, ownership, approvals or legal status.</p>"""
    ld = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":['
          f'{{"@type":"ListItem","position":1,"name":"{E(c["name_en"])}"}},{{"@type":"ListItem","position":2,"name":"{E(loc["name_en"])}","item":"{E(canonical)}"}}]}}</script>')
    robots = "index,follow" if await indexable(loc, len(props)) else "noindex,follow"
    return page(title, body, desc, canonical, robots, ld)


@router.get("/sitemap.xml")
async def sitemap(request: Request):
    base = base_url(request)
    urls = [f"{base}/api/legal/privacy", f"{base}/api/legal/terms"]
    async for c in db.cities.find({"is_active": True}, {"_id": 0}):
        async for loc in db.localities.find({"city_id": c["id"], "is_active": True}, {"_id": 0}):
            n = await db.properties.count_documents({"locality_id": loc["id"], "listing_status": "active", "is_demo": {"$ne": True}})
            if await indexable(loc, n):
                urls.append(f"{base}/api/l/{c['slug']}/{loc['slug']}")
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{E(u)}</loc></url>" for u in urls) + "</urlset>"
    return Response(xml, media_type="application/xml")
