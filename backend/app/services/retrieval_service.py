"""
Core retrieval: turn a user's style profile into nearest-neighbor outfits.

Flow:
  1. Build a query text string from profile fields (same style as build_embeddings.py)
  2. Embed that text
  3. Ask Chroma for the top_k most similar outfit vectors
  4. Return outfit ids + metadata + distance for the next LLM step
"""

from app.vector_store.client import get_chroma_collection
from app.vector_store.embedder import embed_text


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


def retrieve_candidate_outfits(
    style_tags: dict,
    color_prefs: list[str],
    fit_pref: str,
    sleeve_pref: str,
    top_k: int = 15,
    exclude_ids: set[int] | None = None,
) -> list[dict]:
    """
    Return top_k outfits from Chroma that are closest to this profile.

    exclude_ids: outfit IDs already swiped by this user (any decision). Filtered
    out BEFORE truncating to top_k so exclusions don't shrink the shortlist.

    Each result dict has:
      - outfit_id (int)
      - category, style_tags, color_tags, formality_level (from Chroma metadata)
      - distance (float — lower means more similar for Chroma's default metric)
    """
    exclude_ids = exclude_ids or set()
    query_text = _build_query_text(style_tags, color_prefs, fit_pref, sleeve_pref)
    query_vector = embed_text(query_text)

    collection = get_chroma_collection()  # connecting to chroma

    # Over-fetch so we can drop swiped IDs and still fill top_k when possible.
    catalog_size = collection.count()
    n_fetch = min(catalog_size, top_k + len(exclude_ids)) if catalog_size else top_k
    if n_fetch <= 0:
        return []

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=n_fetch,
        include=["metadatas", "distances"],
    )

    # Chroma returns lists-of-lists (one inner list per query). We sent one query.
    ids = results["ids"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    candidates: list[dict] = []
    for doc_id, meta, distance in zip(ids, metadatas, distances):
        outfit_id = int(doc_id)
        if outfit_id in exclude_ids:
            continue
        candidates.append(
            {
                "outfit_id": outfit_id,
                "category": meta.get("category"),
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
