"""Read-only checks. Never loads dotenv, starts apps, or contacts providers."""
import json
import os
from pathlib import Path
root = Path(__file__).resolve().parents[1]
checks = []
def check(name, passed):
    checks.append(passed)
    print(("PASS " if passed else "BLOCKED ") + name)
app = json.loads((root / "frontend/app.json").read_text(encoding="utf-8-sig"))["expo"]
eas = json.loads((root / "frontend/eas.json").read_text(encoding="utf-8-sig"))
check("Android application ID", app["android"]["package"] == "com.landvilla.app")
check("Production Android App Bundle", eas["build"]["production"]["android"]["buildType"] == "app-bundle")
check("Production version increment", eas["build"]["production"].get("autoIncrement") is True)
for name in ("GOOGLE_PLAY_BILLING_ENABLED", "GOOGLE_PLAY_PUBSUB_AUDIENCE", "GOOGLE_PLAY_PUBSUB_SERVICE_ACCOUNT"):
    check(name + " configured in process environment", bool(os.getenv(name)))
check("Billing explicitly enabled", os.getenv("GOOGLE_PLAY_BILLING_ENABLED") == "true")
check("HTTPS web origin configured", os.getenv("WEB_ORIGIN", "").startswith("https://"))
check("Demo inventory disabled", os.getenv("SEED_DEMO_LISTINGS") == "false")
check("Startup seeding disabled", os.getenv("SEED_ON_STARTUP") == "false")
print("Manual prerequisites: approved Play products/prices, licensed testers, signed track build, ADC permissions, authenticated Pub/Sub push, replica-set transactions, legal/refund policy, staging region approval.")
raise SystemExit(0 if all(checks) else 1)
