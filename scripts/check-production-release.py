"""Offline release preflight. Prints setting names only; no dotenv or provider calls."""
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from production_runtime import validate_environment

failed = False
try:
    validate_environment({**os.environ, "APP_ENV": "production"})
    print("PASS production boundaries")
except (RuntimeError, ValueError):
    print("BLOCKED production environment: configure required names in docs/RELEASE_OPERATIONS.md")
    failed = True
for name in ("IDENTITY_ENABLED", "OTP_HMAC_SECRET", "GOOGLE_CLIENT_IDS", "FORWARDED_ALLOW_IPS"):
    valid = bool(os.getenv(name)) and (name != "IDENTITY_ENABLED" or os.getenv(name) == "true")
    print(("PASS " if valid else "BLOCKED ") + name)
    failed |= not valid
print("Manual gates: transaction permission test on isolated staging, private R2 policy, signed AAB, Play access, region approval, legal approval, backup restore drill")
raise SystemExit(int(failed))
