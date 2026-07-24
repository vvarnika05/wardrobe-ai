"""
load_outfits_to_db.py
---------------------
Reads data/outfit_dataset/metadata.json (produced by build_outfit_dataset.py)
and inserts each item as a row in the Outfit table.

By default, if the Outfit table already has rows, the script exits without
changing anything (safe to re-run). Pass --force to delete all outfits and
reload from the JSON file.

This does NOT create embeddings or talk to Chroma — that is a later step.

Usage (from the backend/ folder, with .env configured):
    python scripts/load_outfits_to_db.py
    python scripts/load_outfits_to_db.py --force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python scripts/load_outfits_to_db.py` to import the app package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401  — registers Outfit on Base.metadata
from app.db.session import SessionLocal
from app.models.outfit import Outfit

BACKEND_DIR = Path(__file__).resolve().parents[1]
METADATA_JSON = BACKEND_DIR / "data" / "outfit_dataset" / "metadata.json"


def load_metadata() -> list[dict]:
    if not METADATA_JSON.exists():
        raise FileNotFoundError(
            f"{METADATA_JSON} not found. Run scripts/build_outfit_dataset.py first."
        )
    with METADATA_JSON.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("metadata.json must be a JSON list of outfit objects")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Load outfit_dataset into the Outfit table")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete all existing Outfit rows, then reload from metadata.json",
    )
    args = parser.parse_args()

    items = load_metadata()
    print(f"Loaded {len(items)} items from {METADATA_JSON}")

    db = SessionLocal()
    try:
        existing_count = db.query(Outfit).count()
        if existing_count > 0 and not args.force:
            print(
                f"Outfit table already has {existing_count} rows. "
                "Skipping insert. Re-run with --force to wipe and reload."
            )
            return

        if existing_count > 0 and args.force:
            # Wipe first so we don't duplicate rows on reload.
            deleted = db.query(Outfit).delete()
            db.commit()
            print(f"--force: deleted {deleted} existing Outfit rows")

        inserted = 0
        for item in items:
            outfit = Outfit(
                image_url=item["image_url"],
                category=item["category"],
                style_tags=item.get("style_tags"),
                formality_level=item.get("formality_level"),
                color_tags=item.get("color_tags"),
                embedding_id=None,  # filled later when we add Chroma/embeddings
            )
            db.add(outfit)
            inserted += 1

        db.commit()
        print(f"Inserted {inserted} outfits into the database.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
