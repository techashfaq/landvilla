"""Demo visibility is a read policy, never a destructive startup migration."""


def public_property_filter(include_demo: bool) -> dict:
    real = {"listing_status": "active", "is_demo": {"$ne": True}}
    if not include_demo:
        return real
    return {"$or": [real, {"is_demo": True, "listing_status": {"$in": ["active", "demo_hidden"]}}]}
