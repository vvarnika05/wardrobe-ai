"""
Thin wrapper around the Gemini API.

All LLM calls in this project should go through generate_structured_response().
If we swap providers later (OpenAI, Claude, etc.), only this file needs to change.
"""

import json
import re

import google.generativeai as genai

from app.config import settings

# Configure the SDK once at import time using our settings.
genai.configure(api_key=settings.GEMINI_API_KEY)

# gemini-1.5-flash is fast and cheap — good enough for dev.
# Swap the model name here if we upgrade later.
_MODEL_NAME = "gemini-2.5-flash"


def generate_structured_response(prompt: str) -> dict | list:
    """
    Send a prompt to Gemini and return the response parsed as JSON
    (a Python dict OR list, depending on what the prompt asks for).

    The prompt should ask for JSON. We also set response_mime_type so Gemini
    is more likely to return raw JSON (no markdown fences).
    """
    model = genai.GenerativeModel(
        model_name=_MODEL_NAME,
        generation_config={
            # Ask the API to emit JSON only — reduces "```json ... ```" wrappers.
            "response_mime_type": "application/json",
            "temperature": 0.2,
        },
    )

    response = model.generate_content(prompt)
    raw_text = (response.text or "").strip()

    # Safety net: if the model still wraps JSON in markdown fences, strip them.
    cleaned = _strip_markdown_fences(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Gemini returned invalid JSON. Parse error: {exc}. Raw response: {raw_text!r}"
        ) from exc

    # Recommendation prompts ask for a JSON array; profile parsing asks for an object.
    if not isinstance(data, (dict, list)):
        raise ValueError(
            f"Expected a JSON object or array, got {type(data).__name__}: {data!r}"
        )

    return data


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers if present."""
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    return text
