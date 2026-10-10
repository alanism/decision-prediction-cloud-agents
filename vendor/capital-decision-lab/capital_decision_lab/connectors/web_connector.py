"""Standard-library public HTTP retrieval capability."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def retrieve_public_url(request, *, timeout: float = 15.0) -> dict:
    if not request.source_url:
        raise ValueError("SOURCE_URL_REQUIRED")
    parsed = urlparse(request.source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("PUBLIC_HTTP_URL_REQUIRED")
    host = parsed.hostname.casefold()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise ValueError("PRIVATE_NETWORK_TARGET_FORBIDDEN")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
        raise ValueError("PRIVATE_NETWORK_TARGET_FORBIDDEN")
    http_request = Request(request.source_url, headers={"User-Agent": "CapitalDecisionLab/0.1"})
    with urlopen(http_request, timeout=timeout) as response:  # nosec: user-directed public research URL
        content = response.read(2_000_000).decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    return {"raw_content": content, "extracted_fields": {}, "confidence": 0.7, "limitations": ["Raw public response requires source-specific extraction."]}
