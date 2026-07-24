"""
Recommendation engine: retrieval shortlist + trends + Gemini ranking
→ final swipe deck constrained to real candidate outfit IDs.
"""

from __future__ import annotations

import json

from app.services.retrieval_service import retrieve_candidate_outfits
from app.services.trend_service import get_current_trends
from app.utils.llm_client import generate_structured_response
from app.utils.validators import validate_llm_outfit_selection


def _build_recommendation_prompt(
    profile: dict,
    color_prefs: list[str],
    fit_pref: str,
    sleeve_pref: str,
    candidates: list[dict],
    trends: list[str],
    deck_size: int,
) -> str:
    # Strip internal fields (distance) — LLM only needs outfit facts.
    candidates_for_prompt = [
        {
            "outfit_id": c["outfit_id"],
            "category": c.get("category"),
            "color_tags": c.get("color_tags") or [],
            "formality_level": c.get("formality_level"),
        }
        for c in candidates
    ]
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

Current trends (manually curated — use as soft inspiration, not hard rules):
{json.dumps(trends, indent=2)}

Candidate outfits (these are the ONLY outfits you may choose from):
{json.dumps(candidates_for_prompt, indent=2)}

Allowed outfit_id values (copy from this list only): {candidate_ids}

Task:
- Select and RANK the best {deck_size} outfits from the candidates above.
- Consider the user profile first, then whether a pick gently fits current trends.
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
) -> list[dict]:
    """
    Build a ranked swipe deck for this profile.

    Returns a list of dicts:
      {outfit_id, category, color_tags, formality_level, reason}
    """
    # a) Retrieve more candidates than we show so the LLM can filter weak matches.
    candidates = retrieve_candidate_outfits(
        style_tags=profile,
        color_prefs=color_prefs,
        fit_pref=fit_pref,
        sleeve_pref=sleeve_pref,
        top_k=15,
    )
    if not candidates:
        raise ValueError("No candidate outfits returned from retrieval.")

    # b) Load static trends.
    trends = get_current_trends()

    # c) Build the Gemini prompt.
    prompt = _build_recommendation_prompt(
        profile=profile,
        color_prefs=color_prefs,
        fit_pref=fit_pref,
        sleeve_pref=sleeve_pref,
        candidates=candidates,
        trends=trends,
        deck_size=deck_size,
    )

    # d) Call Gemini (reuses existing llm_client — no duplicate SDK setup).
    llm_raw = generate_structured_response(prompt)

    # generate_structured_response may return a list directly, or a dict wrapper.
    if isinstance(llm_raw, dict):
        # Soft unwrap common shapes like {"outfits": [...]} / {"selections": [...]}
        for key in ("outfits", "selections", "recommendations", "items"):
            if isinstance(llm_raw.get(key), list):
                llm_raw = llm_raw[key]
                break
        else:
            raise ValueError(
                f"Expected a JSON list of picks (or a dict with an outfits list), got keys: {list(llm_raw.keys())}"
            )

    # e) Validate: drop invented IDs / bad shapes.
    valid_ids = {c["outfit_id"] for c in candidates}
    validated = validate_llm_outfit_selection(llm_raw, valid_ids)

    # f) Merge reasons back onto full candidate metadata (don't trust LLM to repeat fields).
    by_id = {c["outfit_id"]: c for c in candidates}
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
            }
        )

    # g) Cap at deck_size (LLM may return extras; we asked for deck_size).
    return merged[:deck_size]
