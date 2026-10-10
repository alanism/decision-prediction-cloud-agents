"""Source-specific host extraction adapters."""

from .broker_margin import extract_broker_margin
from .manual_note import extract_manual_note
from .polymarket import extract_polymarket
from .portfolio_table import extract_portfolio_table
from .reddit import extract_reddit
from .x_twitter import extract_x_twitter

EXTRACTORS = {
    "polymarket": extract_polymarket, "x_twitter": extract_x_twitter,
    "reddit": extract_reddit, "portfolio": extract_portfolio_table,
    "broker_margin": extract_broker_margin, "manual_note": extract_manual_note,
}

__all__ = ["EXTRACTORS"]
