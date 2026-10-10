"""Normalize broker margin screen fields without implying account access."""

from __future__ import annotations

from .common import extraction_bundle, response_fields


def extract_broker_margin(response: dict) -> dict:
    fields, status = response_fields(response)
    required = {"account_equity", "margin_used", "borrowed_amount", "maintenance_margin", "initial_margin", "cash"}
    if not required <= fields.keys():
        raise ValueError("BROKER_MARGIN_FIELDS_MISSING")
    document = {**fields, "verification_status": status, "captured_at": response["retrieval_timestamp"]}
    return extraction_bundle(response, "broker_margin", fields, document)
