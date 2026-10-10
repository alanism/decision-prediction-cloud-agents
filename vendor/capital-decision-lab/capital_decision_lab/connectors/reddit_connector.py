"""Reddit connector routing through API, public JSON, browser, or artifact capabilities."""

from .registry import ConnectorRegistry, RetrievalRequest


def gather(query_or_url: str, capabilities: dict) -> dict:
    return ConnectorRegistry(capabilities).gather(RetrievalRequest("reddit", source_url=query_or_url, query=query_or_url))
