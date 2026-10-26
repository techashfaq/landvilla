"""Iteration 2 regression: locality verification reset, parent loops, merge guards, segment validation, saved 404, demo listings."""
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

_fe = dotenv_values(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = _fe["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") + "/api"
BUYER = {"Authorization": "Bearer test_session_buyer_landvilla"}
ADMIN = {"Authorization": "Bearer test_session_admin_landvilla"}


def req(method, path, h=None, **kw):
    return requests.request(method, f"{BASE_URL}{path}", headers=h or {}, timeout=30, **kw)


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    from pymongo import MongoClient
    be = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    MongoClient(be["MONGO_URL"])[be["DB_NAME"]].localities.delete_many({"name_en": {"$regex": "^TEST"}})


@pytest.fixture(scope="module")
def meta():
    return req("GET", "/meta").json()


def mk(meta, label, **extra):
    tag = uuid.uuid4().hex[:6]
    body = {"name_en": f"TEST {label} {tag}", "name_hi": f"टेस्ट {label} {tag}", "zone_id": meta["zones"][0]["id"], **extra}
    r = req("POST", "/admin/localities", ADMIN, json=body)
    assert r.status_code == 200, r.text
    return r.json()


# Locality PATCH: unchanged core fields keep verified; name change resets to pending
def test_patch_unchanged_core_keeps_verified(meta):
    loc = mk(meta, "Verif")
    v = req("POST", f"/admin/localities/{loc['id']}/verify", ADMIN, json={"source": "TEST ward list"})
    assert v.json()["verification_status"] == "verified"
    p = req("PATCH", f"/admin/localities/{loc['id']}", ADMIN, json={
        "name_en": loc["name_en"], "name_hi": loc["name_hi"], "zone_id": loc["zone_id"], "aliases": ["TESTAliasX" + loc["id"][-4:]]})
    assert p.status_code == 200, p.text
    assert p.json()["verification_status"] == "verified"
    assert p.json()["aliases"] == ["TESTAliasX" + loc["id"][-4:]]
    p2 = req("PATCH", f"/admin/localities/{loc['id']}", ADMIN, json={"name_en": loc["name_en"] + " Renamed"})
    assert p2.status_code == 200 and p2.json()["verification_status"] == "pending"


# Parent loops blocked
def test_parent_loop_blocked(meta):
    a, b = mk(meta, "LoopA"), mk(meta, "LoopB")
    assert req("PATCH", f"/admin/localities/{a['id']}", ADMIN, json={"parent_id": b["id"]}).status_code == 200
    r = req("PATCH", f"/admin/localities/{b['id']}", ADMIN, json={"parent_id": a["id"]})
    assert r.status_code == 400, r.text
    assert req("PATCH", f"/admin/localities/{a['id']}", ADMIN, json={"parent_id": a["id"]}).status_code == 400


# Merge guards: inactive source 404; target whose parent is source isn't self-parented
def test_merge_guards(meta):
    src = mk(meta, "MSrc")
    tgt = mk(meta, "MTgt", parent_id=src["id"])
    m = req("POST", "/admin/localities/merge", ADMIN, json={"source_id": src["id"], "target_id": tgt["id"]})
    assert m.status_code == 200, m.text
    assert m.json()["target"]["parent_id"] != tgt["id"]
    assert m.json()["target"]["parent_id"] is None
    other = mk(meta, "MOther")
    again = req("POST", "/admin/localities/merge", ADMIN, json={"source_id": src["id"], "target_id": other["id"]})
    assert again.status_code == 404
    # inactive target also 404
    req("POST", f"/admin/localities/{other['id']}/deactivate", ADMIN)
    assert req("POST", "/admin/localities/merge", ADMIN, json={"source_id": tgt["id"], "target_id": other["id"]}).status_code == 404


# Segment validation
def test_segment_buy_400():
    assert req("GET", "/properties", params={"segment": "buy"}).status_code == 400
    assert req("GET", "/properties", params={"segment": "residential"}).status_code == 200


# Saved: unknown id 404
def test_save_unknown_404():
    r = req("POST", "/saved/prop_doesnotexist", BUYER)
    assert r.status_code == 404
    assert "prop_doesnotexist" not in [p["id"] for p in req("GET", "/saved", BUYER).json()["items"]]


# Demo listings: 20, buy in Sethi Nagar / Central Ujjain, buy commercial in Freeganj
def test_demo_listings(meta):
    allp = req("GET", "/properties", params={"limit": 50}).json()
    assert allp["total"] == 20
    assert req("GET", "/properties", params={"purpose": "buy", "locality": "sethi-nagar"}).json()["total"] >= 1
    assert req("GET", "/properties", params={"purpose": "buy", "zone": "central-ujjain"}).json()["total"] >= 1
    fr = req("GET", "/properties", params={"purpose": "buy", "locality": "freeganj", "segment": "commercial"})
    assert fr.status_code == 200 and fr.json()["total"] >= 1
