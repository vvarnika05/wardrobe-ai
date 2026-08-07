"""
backfill_outfit_gender.py
-------------------------
Read Kaggle data/raw/styles.csv gender values and update Outfit.gender,
matching by source id in the image filename (…/26588.jpg → 26588).

Also writes gender onto data/outfit_dataset/metadata.json when source_id matches,
so future load_outfits_to_db runs keep the field.

Usage (from backend/):
    python scripts/backfill_outfit_gender.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.db.session import SessionLocal
from app.models.outfit import Outfit

BACKEND_DIR = Path(__file__).resolve().parents[1]
STYLES_CSV = BACKEND_DIR / "data" / "raw" / "styles.csv"
METADATA_JSON = BACKEND_DIR / "data" / "outfit_dataset" / "metadata.json"


def _source_id_from_image_url(image_url: str | None) -> str | None:
    if not image_url:
        return None
    name = image_url.rstrip("/").split("/")[-1]
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return name or None


def load_csv_gender_map() -> dict[str, str]:
    if not STYLES_CSV.exists():
        raise FileNotFoundError(f"Missing {STYLES_CSV}")
    mapping: dict[str, str] = {}
    with STYLES_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            item_id = (row.get("id") or "").strip()
            gender = (row.get("gender") or "").strip()
            if item_id and gender:
                mapping[item_id] = gender
    return mapping


def main() -> None:
    gender_by_id = load_csv_gender_map()
    print(f"Loaded {len(gender_by_id)} gender rows from {STYLES_CSV}")

    db = SessionLocal()
    updated = 0
    missing_csv = 0
    already = 0
    dist: Counter[str] = Counter()

    try:
        outfits = db.query(Outfit).order_by(Outfit.id).all()
        print(f"Outfits in DB: {len(outfits)}")

        for outfit in outfits:
            source_id = _source_id_from_image_url(outfit.image_url)
            gender = gender_by_id.get(source_id or "")
            if not gender:
                missing_csv += 1
                continue
            if outfit.gender == gender:
                already += 1
                dist[gender] += 1
                continue
            outfit.gender = gender
            updated += 1
            dist[gender] += 1

        db.commit()
    finally:
        db.close()

    # Keep metadata.json in sync for future --force reloads.
    meta_updated = 0
    if METADATA_JSON.exists():
        items = json.loads(METADATA_JSON.read_text(encoding="utf-8"))
        if isinstance(items, list):
            for item in items:
                sid = str(item.get("source_id") or "").strip()
                if not sid:
                    # Fall back to filename in image_url
                    sid = _source_id_from_image_url(item.get("image_url")) or ""
                gender = gender_by_id.get(sid)
                if gender and item.get("gender") != gender:
                    item["gender"] = gender
                    meta_updated += 1
                elif gender and "gender" not in item:
                    item["gender"] = gender
                    meta_updated += 1
            METADATA_JSON.write_text(
                json.dumps(items, indent=2) + "\n", encoding="utf-8"
            )

    print()
    print("Backfill summary:")
    print(f"  DB rows updated:              {updated}")
    print(f"  DB rows already correct:      {already}")
    print(f"  DB rows with no CSV match:    {missing_csv}")
    print(f"  metadata.json fields set:     {meta_updated}")
    print("  Gender distribution (matched DB rows):")
    for g, n in dist.most_common():
        print(f"    {g}: {n}")


if __name__ == "__main__":
    main()
