"""
Validate LLM outfit-selection responses.

Kept separate from recommendation_engine.py so the engine stays focused on
orchestration (retrieve → prompt → merge) and validation stays reusable.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def validate_llm_outfit_selection(
    llm_response: list,
    valid_outfit_ids: set[int],
) -> list[dict]:
    """
    Keep only picks that look like {"outfit_id": int, "reason": str}
    where outfit_id is in valid_outfit_ids.

    Drops invalid items with a warning. Raises ValueError if nothing valid remains.
    """
    if not isinstance(llm_response, list):
        raise ValueError(
            f"Expected LLM response to be a list, got {type(llm_response).__name__}"
        )

    valid_items: list[dict] = []

    for index, item in enumerate(llm_response):
        if not isinstance(item, dict):
            logger.warning(
                "Dropping LLM pick at index %s: expected a dict, got %s (%r)",
                index,
                type(item).__name__,
                item,
            )
            continue

        if "outfit_id" not in item or "reason" not in item:
            logger.warning(
                "Dropping LLM pick at index %s: missing outfit_id and/or reason. Item=%r",
                index,
                item,
            )
            continue

        outfit_id = item["outfit_id"]
        reason = item["reason"]

        # Accept JSON numbers that arrive as ints; reject bools (bool is a subclass of int).
        if isinstance(outfit_id, bool) or not isinstance(outfit_id, int):
            logger.warning(
                "Dropping LLM pick at index %s: outfit_id must be int, got %s (%r)",
                index,
                type(outfit_id).__name__,
                outfit_id,
            )
            continue

        if not isinstance(reason, str) or not reason.strip():
            logger.warning(
                "Dropping LLM pick at index %s: reason must be a non-empty string, got %s (%r)",
                index,
                type(reason).__name__,
                reason,
            )
            continue

        if outfit_id not in valid_outfit_ids:
            logger.warning(
                "Dropping LLM pick at index %s: invented outfit_id %s not in candidate set %s",
                index,
                outfit_id,
                sorted(valid_outfit_ids),
            )
            continue

        valid_items.append({"outfit_id": outfit_id, "reason": reason.strip()})

    if not valid_items:
        raise ValueError(
            "LLM returned no valid outfit selections. "
            "Every pick was missing fields, had wrong types, or used an invented outfit_id."
        )

    return valid_items
