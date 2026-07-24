"""
Text embedding helper.

Loads the sentence-transformers model ONCE at import time.
Calling embed_text() many times reuses that loaded model (loading is slow;
embedding a short string is fast).
"""

from sentence_transformers import SentenceTransformer

# Small, fast, good-enough model for semantic similarity on short fashion tags.
# Loaded once when this module is first imported.
_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> list[float]:
    """Turn a string into a dense vector (list of floats)."""
    vector = _MODEL.encode(text)
    # encode() returns a numpy array — convert so Chroma/JSON can use it.
    return vector.tolist()
