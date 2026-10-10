"""Screenshot extraction adapter; extracted values remain unverified."""

from .registry import ConnectorRegistry, RetrievalRequest


def gather(path: str, capabilities: dict, *, source_type: str = "screenshot") -> dict:
    return ConnectorRegistry(capabilities).gather(RetrievalRequest(source_type, artifact_path=path))
