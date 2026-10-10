"""Manual and pasted-text capability."""


def manual_capability(request) -> dict:
    if not request.content:
        raise ValueError("MANUAL_CONTENT_REQUIRED")
    return {"raw_content": request.content, "extracted_fields": {}, "confidence": 1.0}
