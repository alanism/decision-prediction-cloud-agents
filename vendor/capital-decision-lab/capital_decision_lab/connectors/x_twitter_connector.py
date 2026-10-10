"""X/Twitter connector routing through user-configured capabilities."""

from .registry import ConnectorRegistry, RetrievalRequest


def gather(query_or_url: str, capabilities: dict) -> dict:
    return ConnectorRegistry(capabilities).gather(RetrievalRequest("x_twitter", source_url=query_or_url, query=query_or_url))
