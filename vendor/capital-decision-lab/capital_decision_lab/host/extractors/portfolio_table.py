"""Normalize portfolio table or screenshot fields into a portfolio snapshot."""

from __future__ import annotations

from .common import extraction_bundle, response_fields


def extract_portfolio_table(response: dict) -> dict:
    fields, status = response_fields(response)
    required = {"cash", "total_equity", "margin_used", "borrowed_amount", "positions"}
    if not required <= fields.keys():
        raise ValueError("PORTFOLIO_REQUIRED_FIELDS_MISSING")
    document = {
        "contract_version": "nhi.portfolio_snapshot.v1", "snapshot_id": f"host_{response['response_id']}",
        "capture_timestamp": response["retrieval_timestamp"], "cash": fields["cash"], "total_equity": fields["total_equity"],
        "margin_used": fields["margin_used"], "borrowed_amount": fields["borrowed_amount"],
        "maintenance_margin_requirement": fields.get("maintenance_margin_requirement", 0.0),
        "initial_margin_requirement": fields.get("initial_margin_requirement", 0.0),
        "portfolio_source": "screenshot" if response["retrieval_method"] == "screenshot" else "pasted_table",
        "positions": fields["positions"], "verification_status": status,
    }
    if fields.get("source_artifact_path"):
        document["source_artifact_path"] = fields["source_artifact_path"]
    if response.get("source_artifact_hash"):
        document["source_artifact_hash"] = response["source_artifact_hash"]
    return extraction_bundle(response, "portfolio", fields, document)
