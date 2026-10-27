# UI seed for iteration 5 (run: cd /app/backend && python -m tests.ui_seed_iter5 [cleanup])
import json
import sys
import uuid

import requests

from tests.test_iteration4_public_e2e import API, mdb, h, free_locality, upload, listing_payload

if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
    s = json.load(open("/tmp/ui5.json"))
    mdb.properties.delete_many({"id": s["pid"]})
    mdb.enquiries.delete_many({"property_id": s["pid"]})
    mdb.abuse_reports.delete_many({"target_id": s["pid"]})
    mdb.deletion_requests.delete_many({"email": {"$in": s["emails"]}})
    mdb.blocks.delete_many({"blocked_id": "user_testbuyer01"})
    print("cleaned")
    sys.exit()

loc = free_locality() or mdb.localities.find_one({"is_active": True})
r = requests.post(f"{API}/listings", headers=h("owner"), json=listing_payload(loc["id"], upload("owner")), timeout=20)
pid = r.json()["id"]
requests.post(f"{API}/admin/listings/{pid}/approve", headers=h("admin"), json={"note": ""}, timeout=20)
e = requests.post(f"{API}/enquiries", headers=h("buyer"), json={"property_id": pid, "name": "Test Buyer", "phone": "9876543210",
                  "message": "TEST_ UI enquiry", "intent": "info", "share_phone_consent": False}, timeout=20).json()
emails = [f"test_ui5_{uuid.uuid4().hex[:5]}@example.com" for _ in range(2)]
for em in emails:
    requests.post(f"{API}/legal/delete-account", data={"email": em}, timeout=20)
requests.post(f"{API}/properties/{pid}/report", headers=h("buyer"), json={"reason": "wrong_info", "note": "TEST_ ui"}, timeout=20)
out = {"pid": pid, "eid": e["id"], "emails": emails}
json.dump(out, open("/tmp/ui5.json", "w"))
print(json.dumps(out))
