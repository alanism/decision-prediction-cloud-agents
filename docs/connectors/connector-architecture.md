# Connector Architecture

Connectors normalize API, browser, scrape, screenshot, paste, file-import, and manual retrieval into one provenance record. The registry tries higher-quality configured capabilities first and records every failed fallback attempt.

Public HTTP retrieval uses the Python standard library. Browser, screenshot extraction, and authenticated services are capability-injected by the upstream host host; credentials are never persisted by this package. Missing capabilities return `blocked_source_unavailable` instead of simulated data.
