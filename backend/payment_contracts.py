"""Payment contract validation: provider responses are never client success claims."""
from fastapi import HTTPException


def captured_payment(payment: dict, order: dict) -> bool:
    if not isinstance(payment, dict) or payment.get("order_id") != order["razorpay_order_id"] or type(payment.get("amount")) is not int or payment["amount"] != order["amount"] or payment.get("currency") != "INR":
        raise HTTPException(400, "Payment does not match order")
    return payment.get("status") == "captured" and bool(payment.get("id"))


def active_plan_filter():
    # Legacy seeded prices need explicit administrative publication, never inferred approval.
    return {"is_active": True, "status": "active"}
