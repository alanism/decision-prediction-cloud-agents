"""Polymarket connector routing through the shared registry."""

from .registry import ConnectorRegistry, RetrievalRequest


def gather(query_or_url: str, capabilities: dict) -> dict:
    return ConnectorRegistry(capabilities).gather(RetrievalRequest("polymarket", source_url=query_or_url, query=query_or_url))
