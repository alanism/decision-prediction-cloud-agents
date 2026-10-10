from __future__ import annotations

from capital_decision_lab.connectors.registry import ConnectorRegistry, RetrievalRequest
from capital_decision_lab.connectors.web_connector import retrieve_public_url


def _capability(method: str):
    def retrieve(request):
        return {"raw_content": f"synthetic {method}", "extracted_fields": {"title": "Synthetic"}, "confidence": 0.8}
    return retrieve


def test_registry_prefers_api_and_records_provenance() -> None:
    registry = ConnectorRegistry({"api": _capability("api"), "browser": _capability("browser")})
    result = registry.gather(RetrievalRequest(source_type="polymarket", source_url="https://example.invalid/market"))
    assert result["status"] == "ok"
    assert result["retrieval_method"] == "api"
    assert result["source_url"] == "https://example.invalid/market"
    assert len(result["raw_content_hash"]) == 64
    assert result["retrieval_timestamp"].endswith("Z")
    assert result["verification_status"] == "auto_retrieved"


def test_registry_falls_back_in_quality_order() -> None:
    def unavailable(_request):
        raise RuntimeError("unavailable")
    registry = ConnectorRegistry({"api": unavailable, "browser": unavailable, "scrape": _capability("scrape")})
    result = registry.gather(RetrievalRequest(source_type="reddit", source_url="https://example.invalid/thread"))
    assert result["retrieval_method"] == "scrape"
    assert [attempt["method"] for attempt in result["attempts"]] == ["api", "browser", "scrape"]


def test_screenshot_requires_verification_and_unavailable_blocks() -> None:
    screenshot = ConnectorRegistry({"screenshot": _capability("screenshot")}).gather(
        RetrievalRequest(source_type="brokerage_screenshot", artifact_path="local/screen.png")
    )
    assert screenshot["verification_status"] == "unverified_extraction"
    unavailable = ConnectorRegistry({}).gather(RetrievalRequest(source_type="news", query="synthetic query"))
    assert unavailable["status"] == "blocked_source_unavailable"
    assert unavailable["verification_status"] == "unavailable"


def test_source_specific_connectors_are_registered() -> None:
    registry = ConnectorRegistry({"manual": _capability("manual")})
    assert {"polymarket", "x_twitter", "reddit", "web", "sec_filing", "screenshot", "local_file", "manual_note"} <= set(registry.source_types)


def test_public_http_connector_rejects_local_and_non_http_targets() -> None:
    import pytest
    with pytest.raises(ValueError, match="PUBLIC_HTTP_URL_REQUIRED"):
        retrieve_public_url(RetrievalRequest("web", source_url="file:///private.txt"))
    with pytest.raises(ValueError, match="PRIVATE_NETWORK_TARGET_FORBIDDEN"):
        retrieve_public_url(RetrievalRequest("web", source_url="http://127.0.0.1:8000/private"))
