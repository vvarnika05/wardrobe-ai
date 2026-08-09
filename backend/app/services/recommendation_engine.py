"""
Recommendation engine: retrieval shortlist + trends + Gemini ranking
→ final swipe deck constrained to real candidate outfit IDs.

When Gemini is unavailable (quota, network, bad payload, etc.), falls back to
color-relevance-sorted Chroma candidates so the swipe feed still loads with
deterministic MATCH-before-MISMATCH ordering (no LLM required).
"""

from __future__ import annotations

import json
import logging

from app.config import settings
from app.services.retrieval_service import retrieve_candidate_outfits
from app.services.trend_service import get_current_trends
from app.utils.llm_client import generate_structured_response
from app.utils.validators import validate_llm_outfit_selection

logger = logging.getLogger(__name__)

# Generic reason when Gemini did not write per-outfit copy.
_FALLBACK_REASON = "Selected based on your saved preferences."


def _colors_overlap(color_tags: list | None, color_prefs: list | None) -> bool:
    """True if any outfit color_tag matches any user color_pref (case-insensitive)."""
    prefs = {str(c).strip().lower() for c in (color_prefs or []) if str(c).strip()}
    if not prefs:
        # No stated prefs → treat everything as a match (don't punish the deck).
        return True
    tags = {str(t).strip().lower() for t in (color_tags or []) if str(t).strip()}
    return bool(prefs & tags)


def rank_by_color_relevance(
    candidates: list[dict],
    color_prefs: list[str] | None,
) -> list[dict]:
    """
    Pure-Python re-sort: COLOR MATCH items first, MISMATCH last.

    Stable within each group (preserves Chroma distance order among matches /
    among mismatches). Does not call Gemini. Sets `color_match` on each dict.
    """
    annotated: list[dict] = []
    for c in candidates:
        item = dict(c)
        item["color_match"] = _colors_overlap(item.get("color_tags"), color_prefs)
        annotated.append(item)
    return sorted(annotated, key=lambda c: (0 if c.get("color_match") else 1))


def _deck_from_ranked_candidates(
    ranked: list[dict],
    deck_size: int,
    reason: str = _FALLBACK_REASON,
) -> list[dict]:
    """Map ranked candidates into the API deck shape (no internal flags)."""
    deck: list[dict] = []
    for c in ranked[:deck_size]:
        deck.append(
            {
                "outfit_id": c["outfit_id"],
                "category": c.get("category"),
                "color_tags": c.get("color_tags") or [],
                "formality_level": c.get("formality_level"),
                "reason": reason,
            }
        )
    return deck


def _build_recommendation_prompt(
    profile: dict,
    color_prefs: list[str],
    fit_pref: str,
    sleeve_pref: str,
    candidates: list[dict],
    trends: list[str],
    deck_size: int,
) -> str:
    # Strip internal fields (distance) — LLM only needs outfit facts + color flag.
    candidates_for_prompt = []
    for c in candidates:
        color_match = bool(c.get("color_match"))
        if "color_match" not in c:
            color_match = _colors_overlap(c.get("color_tags"), color_prefs)
        candidates_for_prompt.append(
            {
                "outfit_id": c["outfit_id"],
                "category": c.get("category"),
                "color_tags": c.get("color_tags") or [],
                "formality_level": c.get("formality_level"),
                "color_relevance": "[COLOR MATCH]" if color_match else "[COLOR MISMATCH]",
            }
        )
    candidate_ids = [c["outfit_id"] for c in candidates_for_prompt]

    user_profile = {
        "aesthetic": profile.get("aesthetic"),
        "formality_range": profile.get("formality_range"),
        "dominant_colors": profile.get("dominant_colors"),
        "pattern_pref": profile.get("pattern_pref"),
        "color_prefs": color_prefs,
        "fit_pref": fit_pref,
        "sleeve_pref": sleeve_pref,
    }

    return f"""
You are a fashion recommendation assistant building a swipe deck.

User profile:
{json.dumps(user_profile, indent=2)}

Current trends (manually curated — soft tie-breakers ONLY):
{json.dumps(trends, indent=2)}

Candidate outfits (these are the ONLY outfits you may choose from).
Each has a color_relevance flag from an exact tag overlap with the user's color_prefs:
{json.dumps(candidates_for_prompt, indent=2)}

Allowed outfit_id values (copy from this list only): {candidate_ids}

Task:
- Select and RANK the best {deck_size} outfits from the candidates above.
- HARD RULE — color_prefs win over trends: the user's explicit color_prefs
  (and [COLOR MATCH] flags) take priority over any trend phrase. Trends like
  "earth tone palettes" or "quiet luxury neutrals" must NEVER justify picking
  a [COLOR MISMATCH] when [COLOR MATCH] candidates remain. Only use trends to
  break ties among otherwise-equal [COLOR MATCH] items (or among mismatches
  only when filling leftover slots).
- Strongly prefer COLOR MATCH items. Only include a COLOR MISMATCH item if there
  are not enough COLOR MATCH candidates to fill the deck, and if you do, the
  reason must acknowledge it's a color departure and explain why (style fit —
  not "because trends prefer neutrals").
- Consider the user profile (especially color_prefs) first; trends are last.
- Write one short sentence "reason" per pick explaining why it fits this user.

Return ONLY valid JSON: a list of objects, each with:
  - "outfit_id": integer (MUST be one of the given candidate IDs: {candidate_ids})
  - "reason": string

No markdown, no code fences, no commentary outside the JSON array.

# Anti-hallucination constraint:
# We restate "must be one of the given candidate IDs" because LLMs sometimes invent
# plausible-looking IDs that are not in the shortlist. Downstream code will drop any
# invented IDs, but the prompt should prevent that in the first place.
""".strip()


def generate_recommendations(
    profile: dict,
    color_prefs: list[str],
    fit_pref: str,
    sleeve_pref: str,
    deck_size: int = 10,
    exclude_ids: set[int] | None = None,
    gender_pref: str | None = None,
) -> tuple[list[dict], bool]:
    """
    Build a ranked swipe deck for this profile.

    Returns (deck, curated_by_ai):
      deck: list of {outfit_id, category, color_tags, formality_level, reason}
      curated_by_ai: True if Gemini ranked the deck; False on color-sorted fallback

    Pipeline:
      1. Chroma retrieve (gender_pref + exclude_ids applied here — independent of Gemini)
      2. Try Gemini rank + validate
      3. On any LLM failure → rank_by_color_relevance() then top deck_size
    """
    # 1) Retrieve — outside the LLM try block. gender_pref is a Chroma `where`
    #    filter inside retrieve_candidate_outfits; it still applies on fallback.
    candidates = retrieve_candidate_outfits(
        style_tags=profile,
        color_prefs=color_prefs,
        fit_pref=fit_pref,
        sleeve_pref=sleeve_pref,
        top_k=15,
        exclude_ids=exclude_ids,
        gender_pref=gender_pref,
    )
    if not candidates:
        return [], False

    effective_deck_size = min(deck_size, len(candidates))
    # Precompute color-sorted shortlist for prompt tagging + fallback.
    ranked = rank_by_color_relevance(candidates, color_prefs)
    fallback = _deck_from_ranked_candidates(ranked, effective_deck_size)

    # 2) Gemini ranking only — any failure → color-sorted fallback (step 3).
    try:
        if getattr(settings, "RECOMMEND_FORCE_FALLBACK", False):
            raise RuntimeError(
                "Forced recommend fallback (RECOMMEND_FORCE_FALLBACK=true)"
            )

        trends = get_current_trends()
        prompt = _build_recommendation_prompt(
            profile=profile,
            color_prefs=color_prefs,
            fit_pref=fit_pref,
            sleeve_pref=sleeve_pref,
            candidates=ranked,  # MATCH-first list for clearer prompt ordering
            trends=trends,
            deck_size=effective_deck_size,
        )

        llm_raw = generate_structured_response(prompt)

        if isinstance(llm_raw, dict):
            for key in ("outfits", "selections", "recommendations", "items"):
                if isinstance(llm_raw.get(key), list):
                    llm_raw = llm_raw[key]
                    break
            else:
                raise ValueError(
                    f"Expected a JSON list of picks (or a dict with an outfits list), got keys: {list(llm_raw.keys())}"
                )

        valid_ids = {c["outfit_id"] for c in ranked}
        validated = validate_llm_outfit_selection(llm_raw, valid_ids)

        by_id = {c["outfit_id"]: c for c in ranked}
        merged: list[dict] = []
        seen: set[int] = set()
        for pick in validated:
            oid = pick["outfit_id"]
            if oid in seen:
                continue
            seen.add(oid)
            source = by_id[oid]
            merged.append(
                {
                    "outfit_id": oid,
                    "category": source.get("category"),
                    "color_tags": source.get("color_tags") or [],
                    "formality_level": source.get("formality_level"),
                    "reason": pick["reason"],
                    "color_match": bool(source.get("color_match")),
                }
            )

        if not merged:
            raise ValueError("LLM returned no valid outfit picks after validation.")

        # Hard guarantee even if the LLM ignored MATCH flags in its ordering.
        merged = rank_by_color_relevance(merged, color_prefs)
        deck = []
        for c in merged[:effective_deck_size]:
            deck.append(
                {
                    "outfit_id": c["outfit_id"],
                    "category": c.get("category"),
                    "color_tags": c.get("color_tags") or [],
                    "formality_level": c.get("formality_level"),
                    "reason": c.get("reason") or _FALLBACK_REASON,
                }
            )
        return deck, True

    except Exception:
        logger.exception(
            "Recommendation LLM unavailable. Falling back to color-sorted "
            "retrieval-only recommendations (curated_by_ai=false)."
        )
        return fallback, False
