"""LANDVILLA API regression tests: meta, search filters, detail, saved, enquiries, admin localities."""
import os
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

_fe = dotenv_values(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = (os.environ.get("EXPO_PUBLIC_BACKEND_URL") or _fe["EXPO_PUBLIC_BACKEND_URL"]).rstrip("/") + "/api"
BUYER = {"Authorization": "Bearer test_session_buyer_landvilla"}
ADMIN = {"Authorization": "Bearer test_session_admin_landvilla"}


def get(path, h=None, **params):
    return requests.get(f"{BASE_URL}{path}", headers=h or {}, params=params, timeout=30)


def post(path, h=None, json=None):
    return requests.post(f"{BASE_URL}{path}", headers=h or {}, json=json, timeout=30)


@pytest.fixture(scope="module", autouse=True)
def cleanup_test_localities():
    """Hard-delete TEST_ localities created by admin tests (no delete API exists)."""
    yield
    from pymongo import MongoClient
    be = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    MongoClient(be["MONGO_URL"])[be["DB_NAME"]].localities.delete_many({"name_en": {"$regex": "^TEST"}})


@pytest.fixture(scope="module")
def meta():
    r = get("/meta")
    assert r.status_code == 200
    return r.json()


def loc_by_slug(meta, slug):
    return next(l for l in meta["localities"] if l["slug"] == slug)


# ---- meta
def test_meta(meta):
    assert meta["city"]["slug"] == "ujjain"
    assert len(meta["zones"]) == 5
    assert len([l for l in meta["localities"] if not l["name_en"].startswith("TEST")]) == 32
    assert len(meta["categories"]) == 6
    assert len(meta["property_types"]) >= 5 and len(meta["amenities"]) >= 5
    assert "'_id'" not in str(meta)
    assert all(l["verification_status"] == "unverified" for l in meta["localities"])


# ---- search
def test_search_purpose_and_demo():
    b = get("/properties", purpose="buy", limit=50).json()
    r = get("/properties", purpose="rent", limit=50).json()
    assert b["total"] > 0 and r["total"] > 0
    assert all(p["purpose"] == "buy" for p in b["items"])
    assert all(p["purpose"] == "rent" for p in r["items"])
    assert b["total"] + r["total"] == get("/properties", limit=50).json()["total"] == len(__import__("seed_data").DEMO_LISTINGS)
    assert all(p.get("is_demo") for p in b["items"] + r["items"])


def test_search_locality_includes_child(meta):
    items = get("/properties", locality="rishi-nagar", limit=50).json()["items"]
    slugs = {p["locality"]["slug"] for p in items}
    assert "rishi-nagar-extension" in slugs and "rishi-nagar" in slugs
    child = get("/properties", locality="rishi-nagar-extension", limit=50).json()["items"]
    assert {p["locality"]["slug"] for p in child} == {"rishi-nagar-extension"}


def test_search_unknown_locality_400():
    assert get("/properties", locality="nowhere-xyz").status_code == 400
    assert get("/properties", zone="nowhere-xyz").status_code == 400


def test_search_zone(meta):
    z = next(z for z in meta["zones"] if z["slug"] == "central-ujjain")
    items = get("/properties", zone="central-ujjain", limit=50).json()["items"]
    assert items and all(p["zone"]["id"] == z["id"] for p in items)


def test_search_price_bhk_sort_type():
    items = get("/properties", min_price=1000000, max_price=5000000, limit=50).json()["items"]
    assert items and all(1000000 <= p["price"] <= 5000000 for p in items)
    items = get("/properties", bhk="4+", limit=50).json()["items"]
    assert all(p["bhk"] >= 4 for p in items)
    items = get("/properties", bhk="1,2", limit=50).json()["items"]
    assert items and all(p["bhk"] in (1, 2) for p in items)
    prices = [p["price"] for p in get("/properties", purpose="buy", sort="price_asc", limit=50).json()["items"]]
    assert prices == sorted(prices)
    prices = [p["price"] for p in get("/properties", purpose="buy", sort="price_desc", limit=50).json()["items"]]
    assert prices == sorted(prices, reverse=True)
    items = get("/properties", type="apartment", limit=50).json()["items"]
    assert items and all(p["type"] == "apartment" for p in items)
    assert get("/properties", type="spaceship").status_code == 400


def test_search_alias_q():
    items = get("/properties", q="Free Ganj", limit=50).json()["items"]
    assert items and all(p["locality"]["slug"] == "freeganj" for p in items)
    items = get("/properties", q="Nanakheda", limit=50).json()["items"]
    assert items


def test_pagination():
    p1 = get("/properties", limit=5, page=1).json()
    p2 = get("/properties", limit=5, page=2).json()
    assert len(p1["items"]) == 5 and len(p2["items"]) == 5
    assert not {x["id"] for x in p1["items"]} & {x["id"] for x in p2["items"]}


# ---- detail
def test_detail_and_404():
    pid = get("/properties", limit=1).json()["items"][0]["id"]
    d = get(f"/properties/{pid}").json()
    assert d["id"] == pid and d["locality"] and "_id" not in d
    assert get("/properties/prop_doesnotexist").status_code == 404


# ---- saved
def test_saved_flow():
    pid = get("/properties", limit=1).json()["items"][0]["id"]
    assert get("/saved").status_code == 401
    assert post(f"/saved/{pid}").status_code == 401
    assert post(f"/saved/{pid}", BUYER).json()["saved"] is True
    ids = [p["id"] for p in get("/saved", BUYER).json()["items"]]
    assert pid in ids
    assert get(f"/properties/{pid}", BUYER).json()["is_saved"] is True
    assert requests.delete(f"{BASE_URL}/saved/{pid}", headers=BUYER, timeout=30).json()["saved"] is False
    assert pid not in [p["id"] for p in get("/saved", BUYER).json()["items"]]
    assert post("/saved/prop_doesnotexist", BUYER).status_code == 404


# ---- enquiries
def test_enquiry_validation_and_auth():
    pid = get("/properties", limit=1).json()["items"][0]["id"]
    good = {"property_id": pid, "name": "TEST User", "phone": "9876543210"}
    assert post("/enquiries", json=good).status_code == 401
    for bad in ({**good, "phone": "12345"}, {**good, "phone": "5876543210"}, {**good, "name": "A"},
                {**good, "phone": "98765432101"}):
        assert post("/enquiries", BUYER, bad).status_code == 422, bad
    assert post("/enquiries", BUYER, {**good, "property_id": "prop_nope"}).status_code == 404


def test_enquiry_create_duplicate_and_list():
    items = get("/properties", limit=50).json()["items"]
    mine = {e["property_id"] for e in get("/enquiries/me", BUYER).json()["items"]}
    target = next((p for p in items if p["id"] not in mine), None)
    if not target:
        pytest.skip("buyer already enquired on all properties in last 24h")
    body = {"property_id": target["id"], "name": "TEST Buyer", "phone": "+91 98765 43210", "intent": "site_visit"}
    r = post("/enquiries", BUYER, body)
    assert r.status_code == 200, r.text
    assert r.json()["phone"] == "9876543210" and r.json()["status"] == "new"
    assert post("/enquiries", BUYER, body).status_code == 409
    lst = get("/enquiries/me", BUYER).json()["items"]
    e = next(x for x in lst if x["id"] == r.json()["id"])
    assert e["property"]["id"] == target["id"]
    assert get("/enquiries/me").status_code == 401


# ---- admin localities
def test_admin_rbac():
    assert get("/admin/localities").status_code == 401
    assert get("/admin/localities", BUYER).status_code == 403
    assert post("/admin/localities", BUYER, {"name_en": "X Y", "name_hi": "x"}).status_code == 403
    r = get("/admin/localities", ADMIN)
    assert r.status_code == 200 and len(r.json()["items"]) >= 32
    assert "listing_count" in r.json()["items"][0]


def test_admin_create_conflict(meta):
    assert post("/admin/localities", ADMIN, {"name_en": "Freeganj", "name_hi": "नया"}).status_code == 409
    assert post("/admin/localities", ADMIN, {"name_en": "TEST Unique Place", "name_hi": "टेस्ट",
                                             "aliases": ["Free Ganj"]}).status_code == 409


def test_admin_full_lifecycle(meta):
    tag = uuid.uuid4().hex[:6]
    zid = meta["zones"][0]["id"]
    a = post("/admin/localities", ADMIN, {"name_en": f"TEST Src {tag}", "name_hi": f"स्रोत {tag}",
                                          "zone_id": zid, "aliases": [f"TSrcAlias{tag}"]})
    assert a.status_code == 200, a.text
    src = a.json()
    assert src["verification_status"] == "unverified" and src["latitude"] is None
    b = post("/admin/localities", ADMIN, {"name_en": f"TEST Tgt {tag}", "name_hi": f"लक्ष्य {tag}", "zone_id": zid})
    tgt = b.json()
    # edit
    p = requests.patch(f"{BASE_URL}/admin/localities/{src['id']}", headers=ADMIN, json={"latitude": 23.1}, timeout=30)
    assert p.status_code == 400
    p = requests.patch(f"{BASE_URL}/admin/localities/{src['id']}", headers=ADMIN,
                       json={"latitude": 23.18, "longitude": 75.78, "geocode_source": "TEST survey"}, timeout=30)
    assert p.status_code == 200 and p.json()["latitude"] == 23.18
    p = requests.patch(f"{BASE_URL}/admin/localities/{src['id']}", headers=ADMIN, json={"aliases": ["Freegunj"]}, timeout=30)
    assert p.status_code == 409
    # verify
    assert post(f"/admin/localities/{src['id']}/verify", ADMIN, {"source": "x"}).status_code == 422
    v = post(f"/admin/localities/{src['id']}/verify", ADMIN, {"source": "TEST municipal ward list"})
    assert v.status_code == 200 and v.json()["verification_status"] == "verified" and v.json()["verified_by"]
    p = requests.patch(f"{BASE_URL}/admin/localities/{src['id']}", headers=ADMIN, json={"name_hi": f"नया {tag}"}, timeout=30)
    assert p.json()["verification_status"] == "pending"
    # deactivate / activate
    assert post(f"/admin/localities/{src['id']}/deactivate", ADMIN).json()["is_active"] is False
    assert src["slug"] not in [l["slug"] for l in get("/meta").json()["localities"]]
    assert get("/properties", locality=src["slug"]).status_code == 400
    assert post(f"/admin/localities/{src['id']}/activate", ADMIN).json()["is_active"] is True
    # merge
    assert post("/admin/localities/merge", ADMIN, {"source_id": src["id"], "target_id": src["id"]}).status_code == 400
    m = post("/admin/localities/merge", ADMIN, {"source_id": src["id"], "target_id": tgt["id"]})
    assert m.status_code == 200 and m.json()["merged"] is True
    assert src["name_en"] in m.json()["target"]["aliases"]
    assert f"TSrcAlias{tag}" in m.json()["target"]["aliases"]
    assert post(f"/admin/localities/{src['id']}/activate", ADMIN).status_code == 400
    # alias of merged source now resolves to target via search q
    adm = get("/admin/localities", ADMIN, q=f"TSrcAlias{tag}").json()["items"]
    assert [x["id"] for x in adm if x["is_active"]] == [tgt["id"]]
    # cleanup: deactivate target
    post(f"/admin/localities/{tgt['id']}/deactivate", ADMIN)
