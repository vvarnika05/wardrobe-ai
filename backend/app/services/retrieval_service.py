"""
Core retrieval: turn a user's style profile into nearest-neighbor outfits.

Flow:
  1. Build a query text string from profile fields (same style as build_embeddings.py)
  2. Embed that text
  3. Ask Chroma for the top_k most similar outfit vectors
     (optional gender_pref → native metadata `where` filter)
  4. Return outfit ids + metadata + distance for the next LLM step
"""

from app.vector_store.client import get_chroma_collection
from app.vector_store.embedder import embed_text

# Profile gender_pref → outfit.gender values included in Chroma `where`.
# Boys/Girls are excluded for men/women so kids' items don't surface.
# "unisex" / unset → no filter (full catalog). Filtering to only Unisex-tagged
# rows would collapse the deck (~2 items in the curated set).
GENDER_PREF_TO_OUTFIT_GENDERS: dict[str, list[str]] = {
    "men": ["Men", "Unisex"],
    "women": ["Women", "Unisex"],
}


def _build_query_text(
    style_tags: dict,
    color_prefs: list[str],
    fit_pref: str,
    sleeve_pref: str,
) -> str:
    """
    Build the search query string from profile fields.

    Keep this format close to the outfit embedding text in build_embeddings.py
    so the vectors live in a similar "language space".
    """
    aesthetic = style_tags.get("aesthetic", "")
    formality = style_tags.get("formality_range", "")
    pattern = style_tags.get("pattern_pref", "")

    # Prefer explicit color_prefs from the profile form; fall back to Gemini's list.
    colors = color_prefs or style_tags.get("dominant_colors") or []
    if isinstance(colors, list):
        colors_str = ", ".join(str(c) for c in colors)
    else:
        colors_str = str(colors)

    # Example:
    # "aesthetic: minimalist, formality: casual to smart-casual, colors: black, beige, white, pattern: solid, fit: relaxed, sleeve: long"
    return (
        f"aesthetic: {aesthetic}, "
        f"formality: {formality}, "
        f"colors: {colors_str}, "
        f"pattern: {pattern}, "
        f"fit: {fit_pref}, "
        f"sleeve: {sleeve_pref}"
    )


def _chroma_gender_where(gender_pref: str | None) -> dict | None:
    """
    Build a Chroma metadata `where` clause for gender_pref, or None to skip filtering.

    gender_pref is clothing-department preference (men/women/unisex), not identity.
    """
    if not gender_pref:
        return None
    key = str(gender_pref).strip().lower()
    allowed = GENDER_PREF_TO_OUTFIT_GENDERS.get(key)
    if not allowed:
        # "unisex" or unknown → no hard filter
        return None
    return {"gender": {"$in": allowed}}


def retrieve_candidate_outfits(
    style_tags: dict,
    color_prefs: list[str],
    fit_pref: str,
    sleeve_pref: str,
    top_k: int = 15,
    exclude_ids: set[int] | None = None,
    gender_pref: str | None = None,
) -> list[dict]:
    """
    Return top_k outfits from Chroma that are closest to this profile.

    exclude_ids: outfit IDs already swiped by this user (any decision). Filtered
    out BEFORE truncating to top_k so exclusions don't shrink the shortlist.

    gender_pref: optional hard filter via Chroma `where` on metadata.gender
    (applied during vector search, not after).

    Each result dict has:
      - outfit_id (int)
      - category, style_tags, color_tags, formality_level, gender (from Chroma metadata)
      - distance (float — lower means more similar for Chroma's default metric)
    """
    exclude_ids = exclude_ids or set()
    query_text = _build_query_text(style_tags, color_prefs, fit_pref, sleeve_pref)
    query_vector = embed_text(query_text)

    collection = get_chroma_collection()  # connecting to chroma

    where = _chroma_gender_where(gender_pref)

    # Over-fetch so we can drop swiped IDs and still fill top_k when possible.
    catalog_size = collection.count()
    n_fetch = min(catalog_size, top_k + len(exclude_ids)) if catalog_size else top_k
    if n_fetch <= 0:
        return []

    query_kwargs: dict = {
        "query_embeddings": [query_vector],
        "n_results": n_fetch,
        "include": ["metadatas", "distances"],
    }
    if where is not None:
        query_kwargs["where"] = where

    results = collection.query(**query_kwargs)

    # Chroma returns lists-of-lists (one inner list per query). We sent one query.
    ids = results["ids"][0] if results.get("ids") else []
    metadatas = results["metadatas"][0] if results.get("metadatas") else []
    distances = results["distances"][0] if results.get("distances") else []

    candidates: list[dict] = []
    for doc_id, meta, distance in zip(ids, metadatas, distances):
        outfit_id = int(doc_id)
        if outfit_id in exclude_ids:
            continue
        candidates.append(
            {
                "outfit_id": outfit_id,
                "category": meta.get("category"),
                "gender": meta.get("gender") or None,
                # Stored as joined strings in Chroma; split back into lists.
                "style_tags": [
                    t.strip()
                    for t in (meta.get("style_tags") or "").split(",")
                    if t.strip()
                ],
                "color_tags": [
                    t.strip()
                    for t in (meta.get("color_tags") or "").split(",")
                    if t.strip()
                ],
                "formality_level": meta.get("formality_level"),
                "distance": distance,
            }
        )
        if len(candidates) >= top_k:
            break

    return candidates
