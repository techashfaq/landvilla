# UI seed for iteration 6 (run: cd /app/backend && python -m tests.ui_seed_iter6 [cleanup])
import json
import sys
import uuid

import requests

from tests.test_iteration4_public_e2e import API, mdb, h, free_locality, upload, listing_payload

if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
    s = json.load(open("/tmp/ui6.json"))
    mdb.properties.delete_many({"id": s["pid"]})
    mdb.enquiries.delete_many({"property_id": s["pid"]})
    mdb.deletion_requests.delete_many({"email": {"$in": s["emails"]}})
    mdb.blocks.delete_many({"blocker_id": {"$in": ["user_testbuyer01", "user_testowner01"]}, "blocked_id": {"$in": ["user_testbuyer01", "user_testowner01"]}})
    print("cleaned")
    sys.exit()

loc = free_locality() or mdb.localities.find_one({"is_active": True})
r = requests.post(f"{API}/listings", headers=h("owner"), json=listing_payload(loc["id"], upload("owner")), timeout=20)
pid = r.json()["id"]
requests.post(f"{API}/admin/listings/{pid}/approve", headers=h("admin"), json={"note": ""}, timeout=20)
e = requests.post(f"{API}/enquiries", headers=h("buyer"), json={"property_id": pid, "name": "Test Buyer", "phone": "9876543210",
                  "message": "TEST_ UI6 enquiry", "intent": "info", "share_phone_consent": False}, timeout=20).json()
requests.post(f"{API}/enquiries/{e['id']}/block", headers=h("owner"), json={}, timeout=20)
emails = [f"test_ui6_{uuid.uuid4().hex[:5]}@example.com" for _ in range(2)]
for em in emails:
    requests.post(f"{API}/legal/delete-account", data={"email": em}, headers={"X-Forwarded-For": f"10.66.{uuid.uuid4().int % 250}.1"}, timeout=20)
dr = requests.get(f"{API}/admin/reports", headers=h("admin"), timeout=20).json()["deletion_requests"]
out = {"pid": pid, "eid": e["id"], "emails": emails, "del_ids": [d["id"] for d in dr if d["email"] in emails]}
json.dump(out, open("/tmp/ui6.json", "w"))
print(json.dumps(out))
