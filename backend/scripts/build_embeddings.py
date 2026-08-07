"""
build_embeddings.py
-------------------
Read every Outfit row from Postgres, embed its tag text into Chroma, and
write the Chroma document id back onto outfit.embedding_id.

This embeds TEXT metadata only (category / tags / colors / formality) —
NOT the image pixels.

Usage (from the backend/ folder):
    python scripts/build_embeddings.py
    python scripts/build_embeddings.py --force   # re-embed everything + rewrite embedding_id
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python scripts/build_embeddings.py` to import the app package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.db.session import SessionLocal
from app.models.outfit import Outfit
from app.vector_store.client import get_chroma_collection
from app.vector_store.embedder import embed_text


def _as_list(value) -> list[str]:
    """Normalize JSON list/dict/None into a flat list of strings for joining."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, dict):
        # Unexpected for style_tags/color_tags on outfits, but don't crash.
        return [str(v) for v in value.values()]
    return [str(value)]


def build_outfit_text(outfit: Outfit) -> str:
    """
    Build the exact text string we embed for one outfit.

    Format (this is what determines retrieval quality):
      "category: Shoes, tags: Sports Shoes, Sports, Summer, Men, color: White, formality: sport"

    Keep this format stable. If you change it, re-run with --force so Chroma
    and the query text in retrieval_service stay aligned.
    """
    style_tags = ", ".join(_as_list(outfit.style_tags))
    color_tags = ", ".join(_as_list(outfit.color_tags))
    formality = outfit.formality_level or ""
    gender = outfit.gender or ""

    return (
        f"category: {outfit.category}, "
        f"tags: {style_tags}, "
        f"color: {color_tags}, "
        f"formality: {formality}, "
        f"gender: {gender}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed outfits into Chroma")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed all outfits and overwrite embedding_id even if already set",
    )
    args = parser.parse_args()

    collection = get_chroma_collection()
    db = SessionLocal()

    embedded = 0
    skipped = 0

    try:
        outfits = db.query(Outfit).order_by(Outfit.id).all()
        total = len(outfits)
        print(f"Found {total} outfits in Postgres")

        # Drop Chroma docs whose ids are no longer in Postgres (e.g. after
        # load_outfits_to_db --force reassigned ids 181–360 while old 1–180 lingered).
        # Without this, /recommend can return stale ids → no DB row → "No image".
        live_ids = {str(o.id) for o in outfits}
        existing = collection.get(include=[])
        orphans = [cid for cid in (existing.get("ids") or []) if cid not in live_ids]
        if orphans:
            # Chroma delete accepts batches; chunk defensively for large catalogs.
            chunk = 100
            for start in range(0, len(orphans), chunk):
                collection.delete(ids=orphans[start : start + chunk])
            print(f"Deleted {len(orphans)} orphan Chroma ids not in Postgres")

        for i, outfit in enumerate(outfits, start=1):
            chroma_id = str(outfit.id)

            # Skip Postgres embedding_id update if already set (unless --force).
            # We still upsert into Chroma so vectors stay present/fresh when forced.
            already_linked = outfit.embedding_id is not None
            if already_linked and not args.force:
                skipped += 1
                if i % 20 == 0 or i == total:
                    print(f"  progress {i}/{total} (embedded={embedded}, skipped={skipped})")
                continue

            text = build_outfit_text(outfit)
            vector = embed_text(text)

            # Chroma metadata values must be scalars (str/int/float/bool) — not lists.
            metadata = {
                "category": outfit.category or "",
                "style_tags": ", ".join(_as_list(outfit.style_tags)),
                "color_tags": ", ".join(_as_list(outfit.color_tags)),
                "formality_level": outfit.formality_level or "",
                # Scalar string for Chroma `where` filters (Men/Women/Boys/Girls/Unisex).
                "gender": outfit.gender or "",
            }

            # upsert = insert or overwrite by id (safe to re-run, no duplicates)
            collection.upsert(
                ids=[chroma_id],
                embeddings=[vector],
                documents=[text],
                metadatas=[metadata],
            )

            outfit.embedding_id = chroma_id
            db.commit()
            embedded += 1

            if i % 20 == 0 or i == total:
                print(f"  progress {i}/{total} (embedded={embedded}, skipped={skipped})")
                # Print one example so you can verify the text format visually.
                if embedded == 1 or i == total:
                    print(f"    example text: {text}")

        print()
        print("Done.")
        print(f"  embedded (upserted + embedding_id set): {embedded}")
        print(f"  skipped (embedding_id already set):     {skipped}")
        print(f"  Chroma collection count:                {collection.count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
