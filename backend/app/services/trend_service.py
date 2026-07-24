"""
Read the manually-maintained trend list from data/trend_data.json.

This file is edited by hand — there is no scraping or scheduled update.
"""

import json
from pathlib import Path

# backend/data/trend_data.json
_TREND_FILE = Path(__file__).resolve().parents[2] / "data" / "trend_data.json"


def get_current_trends() -> list[str]:
    """Return the list of trend strings from trend_data.json (no caching)."""
    with _TREND_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {_TREND_FILE}, got {type(data)}")
    return [str(item) for item in data]
