"""Capability-injected connector registry with ordered fallback."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


RETRIEVAL_ORDER = ("api", "browser", "scrape", "screenshot", "paste", "file_import", "manual")
SOURCE_TYPES = (
    "polymarket", "x_twitter", "reddit", "web", "news", "sec_filing", "company_page",
    "brokerage_screenshot", "portfolio_file", "screenshot", "local_file", "manual_note", "other",
)


@dataclass(frozen=True)
class RetrievalRequest:
    source_type: str
    source_url: str | None = None
    query: str | None = None
    artifact_path: str | None = None
    content: str | None = None


class ConnectorRegistry:
    def __init__(self, capabilities: dict[str, Callable] | None = None):
        self.capabilities = dict(capabilities or {})
        self.source_types = SOURCE_TYPES

    def gather(self, request: RetrievalRequest) -> dict:
        if request.source_type not in SOURCE_TYPES:
            raise ValueError("CONNECTOR_SOURCE_TYPE_UNKNOWN")
        attempts: list[dict] = []
        for method in RETRIEVAL_ORDER:
            capability = self.capabilities.get(method)
            if capability is None:
                continue
            try:
                result = capability(request)
                if not isinstance(result, dict) or "raw_content" not in result:
                    raise ValueError("CONNECTOR_RESULT_INVALID")
            except (OSError, RuntimeError, TypeError, ValueError) as exc:
                attempts.append({"method": method, "status": "failed", "reason": type(exc).__name__})
                continue
            raw = str(result["raw_content"])
            attempts.append({"method": method, "status": "ok"})
            verification = "unverified_extraction" if method == "screenshot" else "user_verified" if method == "manual" else "auto_retrieved"
            return {
                "status": "ok", "source_type": request.source_type,
                "source_url": request.source_url, "source_artifact_path": request.artifact_path,
                "source_artifact_hash": result.get("source_artifact_hash"),
                "retrieval_method": method,
                "retrieval_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "raw_content_hash": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                "extracted_fields": result.get("extracted_fields", {}),
                "confidence": float(result.get("confidence", 0.0)),
                "verification_status": verification,
                "limitations": list(result.get("limitations", [])), "attempts": attempts,
            }
        return {
            "status": "blocked_source_unavailable", "source_type": request.source_type,
            "source_url": request.source_url, "source_artifact_path": request.artifact_path,
            "source_artifact_hash": None, "retrieval_method": "unknown",
            "retrieval_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "raw_content_hash": None, "extracted_fields": {}, "confidence": 0.0,
            "verification_status": "unavailable",
            "limitations": ["No configured connector capability returned source content."], "attempts": attempts,
        }
