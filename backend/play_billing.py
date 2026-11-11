"""Google Play one-time products. Tokens are verified only with Google's server API."""
import hashlib
import os
from urllib.parse import quote
import google.auth
from google.auth.transport.requests import Request as GoogleRequest
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field
import httpx
import server
import marketplace as market
from pymongo.errors import DuplicateKeyError

router = APIRouter(prefix="/api/payments/play")


def enabled():
    if os.getenv("GOOGLE_PLAY_BILLING_ENABLED", "false").lower() != "true":
        raise HTTPException(503, "Google Play purchases are not configured yet")


def account_id(user_id):
    return hashlib.sha256(("landvilla:" + user_id).encode()).hexdigest()


def access_token():
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/androidpublisher"])
    credentials.refresh(GoogleRequest())
    return credentials.token


async def purchase_details(token):
    enabled()
    try:
        access = await run_in_threadpool(access_token)
        package = os.getenv("GOOGLE_PLAY_PACKAGE_NAME", "com.landvilla.app")
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{quote(package, safe='')}/purchases/productsv2/tokens/{quote(token, safe='')}", headers={"Authorization": "Bearer " + access})
        if r.status_code != 200: raise ValueError()
        data = r.json()
        if not isinstance(data, dict): raise ValueError()
        return data
    except Exception:
        raise HTTPException(503, "Google Play verification unavailable. Keep the purchase and retry") from None


class Intent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    property_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    plan_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{16,100}$")


@router.post("/intent")
async def intent(body: Intent, user: dict = Depends(server.current_user)):
    enabled()
    prop = await server.db.properties.find_one({"id": body.property_id, "owner_user_id": user["user_id"], "listing_status": "active", "is_demo": {"$ne": True}})
    if not prop: raise HTTPException(400, "Only your approved real listings are eligible")
    if prop.get("posted_by_role") == "broker" and not await market.broker_profile(user["user_id"]):
        raise HTTPException(403, "Broker approval required")
    if prop.get("posted_by_role") == "broker":
        broker = await market.broker_profile(user["user_id"])
        if broker.get("status") != "approved": raise HTTPException(403, "Broker approval required")
    plan = await server.db.featured_plans.find_one({"id": body.plan_id, **market.active_plan_filter()})
    if not plan or not plan.get("play_product_id"): raise HTTPException(400, "Package is not configured in Google Play")
    oid = "play_" + hashlib.sha256(f"{user['user_id']}:{body.idempotency_key}".encode()).hexdigest()[:32]
    doc = {"_id": oid, "id": oid, "user_id": user["user_id"], "property_id": prop["id"], "plan_id": plan["id"], "plan_slug": plan["slug"], "duration_days": plan["duration_days"], "play_product_id": plan["play_product_id"], "provider": "google_play", "amount": None, "currency": None, "status": "pending", "mode": "play", "razorpay_order_id": "play_" + oid, "created_at": server.now(), "updated_at": server.now()}
    try: await server.db.payment_orders.insert_one(doc)
    except DuplicateKeyError:
        doc = await server.db.payment_orders.find_one({"_id": oid})
        if doc["property_id"] != body.property_id or doc["plan_id"] != body.plan_id or doc["status"] != "pending":
            raise HTTPException(409, "Check purchase history before starting another purchase")
    return {"id": oid, "product_id": doc["play_product_id"], "account_id": account_id(user["user_id"]), "profile_id": oid}


class Receipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purchase_token: str = Field(min_length=10, max_length=4096)


@router.post("/verify")
async def verify(body: Receipt, user: dict = Depends(server.current_user)):
    data = await purchase_details(body.purchase_token)
    if data.get("obfuscatedExternalAccountId") != account_id(user["user_id"]):
        raise HTTPException(403, "Purchase belongs to another account")
    order = await server.db.payment_orders.find_one({"id": data.get("obfuscatedExternalProfileId"), "user_id": user["user_id"], "provider": "google_play"}, {"_id": 0})
    if not order: raise HTTPException(404, "Purchase intent not found")
    lines = data.get("productLineItem", [])
    if len(lines) != 1 or lines[0].get("productId") != order["play_product_id"] or lines[0].get("productOfferDetails", {}).get("quantity", 1) != 1:
        raise HTTPException(400, "Purchase does not match the selected package")
    state = data.get("purchaseStateContext", {}).get("purchaseState")
    if state == "PENDING": return {**market.pay_view(order), "status": "pending"}
    if state != "PURCHASED": raise HTTPException(409, "Google Play has not confirmed this purchase")
    if not data.get("testPurchaseContext") and os.getenv("ALLOW_LIVE_PAYMENTS", "false").lower() != "true":
        raise HTTPException(503, "Live payments are disabled")
    digest = hashlib.sha256(body.purchase_token.encode()).hexdigest()
    claimed = await server.db.payment_orders.update_one({"id": order["id"], "$or": [{"play_receipt_hash": {"$exists": False}}, {"play_receipt_hash": digest}]}, {"$set": {"play_receipt_hash": digest}})
    if not claimed.matched_count:
        raise HTTPException(409, "Another purchase is already assigned to this intent")
    try: await server.db.payment_receipts.insert_one({"_id": digest, "order_id": order["id"], "user_id": user["user_id"]})
    except DuplicateKeyError:
        previous = await server.db.payment_receipts.find_one({"_id": digest})
        if previous["order_id"] != order["id"]: raise HTTPException(409, "Purchase has already been assigned")
    result = await market.fulfil(order, "google_" + digest, "google_play")
    return {**market.pay_view(result), "provider": "google_play"}

@router.post("/notifications")
async def notifications(request: server.Request):
    import base64
    import json
    from google.oauth2 import id_token
    audience = os.getenv("GOOGLE_PLAY_PUBSUB_AUDIENCE", "")
    sender = os.getenv("GOOGLE_PLAY_PUBSUB_SERVICE_ACCOUNT", "")
    if not audience or not sender: raise HTTPException(503, "Play notifications are not configured")
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "): raise HTTPException(401, "Notification authentication required")
    try:
        claims = await run_in_threadpool(id_token.verify_oauth2_token, authorization[7:], GoogleRequest(), audience)
        if claims.get("email") != sender or claims.get("email_verified") is not True: raise ValueError()
    except Exception:
        raise HTTPException(401, "Invalid notification authentication") from None
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 65536: raise HTTPException(413, "Notification too large")
    try:
        envelope = json.loads(raw)
        message = envelope["message"]
        event = json.loads(base64.b64decode(message["data"], validate=True))
        if event.get("packageName") != os.getenv("GOOGLE_PLAY_PACKAGE_NAME", "com.landvilla.app"): raise ValueError()
        event_id = "play_" + str(message["messageId"])
        if len(event_id) > 200: raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise HTTPException(400, "Invalid notification") from None
    if await server.db.payment_webhook_events.find_one({"_id": event_id, "processed": True}): return {"ok": True, "duplicate": True}
    notification = event.get("oneTimeProductNotification") or event.get("voidedPurchaseNotification")
    if not notification:
        if event.get("testNotification") is not None: return {"ok": True}
        raise HTTPException(400, "Unsupported notification")
    if not isinstance(notification, dict): raise HTTPException(400, "Invalid notification")
    token = notification.get("purchaseToken")
    if not isinstance(token, str) or not 10 <= len(token) <= 4096: raise HTTPException(400, "Invalid purchase token")
    data = await purchase_details(token)
    order = await server.db.payment_orders.find_one({"id": data.get("obfuscatedExternalProfileId"), "provider": "google_play"}, {"_id": 0})
    if not order:
        receipt = await server.db.payment_receipts.find_one({"_id": hashlib.sha256(token.encode()).hexdigest()})
        if receipt: order = await server.db.payment_orders.find_one({"id": receipt["order_id"]}, {"_id": 0})
    if not order: raise HTTPException(503, "Purchase intent unavailable; retry notification")
    state = data.get("purchaseStateContext", {}).get("purchaseState")
    if state == "CANCELLED":
        if order["status"] in ("paid", "payment_review"): await market.apply_full_refund(order, "google_" + event_id)
        else: await server.db.payment_orders.update_one({"id": order["id"], "status": {"$nin": ["paid", "refunded"]}}, {"$set": {"status": "cancelled", "updated_at": server.now()}})
    elif state == "PURCHASED":
        user = await server.db.users.find_one({"user_id": order["user_id"]}, {"_id": 0})
        if not user: raise HTTPException(409, "Account requires reconciliation")
        verified = await verify(Receipt(purchase_token=token), user)
        if verified["status"] != "paid": raise HTTPException(503, "Entitlement requires reconciliation before consumption")
        # Consume only after the transactional entitlement commit, even with the app closed.
        line = data.get("productLineItem", [{}])[0]
        if line.get("productOfferDetails", {}).get("consumptionState") != "CONSUMPTION_STATE_CONSUMED":
            try:
                access = await run_in_threadpool(access_token)
                package = os.getenv("GOOGLE_PLAY_PACKAGE_NAME", "com.landvilla.app")
                async with httpx.AsyncClient(timeout=20) as client:
                    response = await client.post(f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{quote(package, safe='')}/purchases/products/{quote(order['play_product_id'], safe='')}/tokens/{quote(token, safe='')}:consume", headers={"Authorization": "Bearer " + access})
                if response.status_code not in (200, 204): raise ValueError()
            except Exception:
                raise HTTPException(503, "Purchase consumption requires retry") from None
    elif state != "PENDING": raise HTTPException(503, "Purchase state unavailable")
    await server.db.payment_webhook_events.update_one({"_id": event_id}, {"$set": {"event_id": event_id, "event": "google_play." + state.lower(), "order_id": order["id"], "processed": True, "processed_at": server.now()}}, upsert=True)
    return {"ok": True}
