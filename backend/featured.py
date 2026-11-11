"""Read-only featured entitlement projection shared by public listing reads."""
from datetime import datetime, timezone


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def effective_featured(prop: dict, cutoff: datetime) -> bool:
    expiry = prop.get("featured_until")
    start = prop.get("featured_from")
    if start is not None and (not isinstance(start, datetime) or utc(start) > utc(cutoff)):
        return False
    # Unknown legacy types fail closed; do not interpret strings as entitlements.
    return prop.get("featured") is True and (
        expiry is None or isinstance(expiry, datetime) and utc(expiry) > utc(cutoff)
    )


def featured_projection(cutoff: datetime) -> dict:
    """Replace only the result's public flag; never update persisted records.

    $type guards against MongoDB's cross-type comparison ordering. Missing/null
    deadlines preserve legacy/demo compatibility; all other non-dates fail closed.
    """
    return {"$addFields": {"featured": {"$and": [
        {"$eq": [{"$ifNull": ["$featured", False]}, True]},
        {"$or": [{"$eq": [{"$ifNull": ["$featured_from", None]}, None]}, {"$cond": [{"$eq": [{"$type": "$featured_from"}, "date"]}, {"$lte": ["$featured_from", utc(cutoff)]}, False]}]},
        {"$or": [
            {"$eq": [{"$ifNull": ["$featured_until", None]}, None]},
            {"$cond": [
                {"$eq": [{"$type": "$featured_until"}, "date"]},
                {"$gt": ["$featured_until", utc(cutoff)]},
                False,
            ]},
        ]},
    ]}}}
