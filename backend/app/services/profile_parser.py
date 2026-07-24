"""
Turn a free-text style description into structured tags via Gemini.

This keeps prompt design out of the route handlers so the API code stays simple.
"""

from app.utils.llm_client import generate_structured_response


def parse_style_profile(style_description: str) -> dict:
    """
    Ask Gemini to read the user's style blurb and return structured JSON tags.

    Expected keys in the returned dict:
      - aesthetic
      - formality_range
      - dominant_colors
      - pattern_pref
    """
    # Each instruction below exists for a reason — leave them readable.
    prompt = f"""
You are a fashion stylist assistant. Read the user's free-text style description
and extract structured preferences.

Return ONLY a valid JSON object. No markdown, no code fences, no commentary.

JSON schema (use exactly these keys):
{{
  "aesthetic": "<string — closest match or short combo, e.g. minimalist, streetwear, formal, boho>",
  "formality_range": "<string — e.g. casual to semi-formal>",
  "dominant_colors": ["<color>", "..."],
  "pattern_pref": "<string — one of: solid, patterned, mixed>"
}}

Why these fields:
- aesthetic: maps free text to a searchable style label for outfit matching later.
- formality_range: helps filter outfits by occasion without being a single rigid level.
- dominant_colors: colors the user leans toward (even if they didn't list hex codes).
- pattern_pref: solids vs prints matter a lot for recommendations.

User style description:
\"\"\"{style_description}\"\"\"
""".strip()

    return generate_structured_response(prompt)
