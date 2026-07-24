"""
ChromaDB client setup.

Uses embedded (local) mode — no separate Chroma server process.
Vectors live on disk under backend/data/chroma_store/.
"""

from pathlib import Path

import chromadb

# backend/data/chroma_store/
_CHROMA_DIR = Path(__file__).resolve().parents[2] / "data" / "chroma_store"
_COLLECTION_NAME = "outfits"

# PersistentClient writes vectors to disk so they survive restarts.
_client = chromadb.PersistentClient(path=str(_CHROMA_DIR))


def get_chroma_collection():
    """Return the 'outfits' collection, creating it if it doesn't exist yet."""
    return _client.get_or_create_collection(name=_COLLECTION_NAME)
