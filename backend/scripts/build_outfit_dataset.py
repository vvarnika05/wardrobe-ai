"""
build_outfit_dataset.py
-----------------------
Reads the Kaggle fashion dump under data/raw/ (styles.csv + images/),
normalizes rows into our Outfit-shaped JSON, samples ~180 diverse items,
and writes data/outfit_dataset/metadata.json.

This does NOT talk to the database and does NOT compute embeddings.
Run load_outfits_to_db.py after this to insert rows into Postgres.

Usage (from the backend/ folder):
    python scripts/build_outfit_dataset.py
"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

# Paths relative to backend/ (the script's parent of scripts/)
BACKEND_DIR = Path(__file__).resolve().parents[1]

# Actual Kaggle dump lives here (styles.csv + images/).
# data/raw_dataset/ is reserved if you add another dump later.
RAW_DIR = BACKEND_DIR / "data" / "raw"
STYLES_CSV = RAW_DIR / "styles.csv"
IMAGES_DIR = RAW_DIR / "images"

OUTPUT_DIR = BACKEND_DIR / "data" / "outfit_dataset"
OUTPUT_JSON = OUTPUT_DIR / "metadata.json"

# Target size for v1 — enough variety without loading all 44k rows.
TARGET_COUNT = 180
RANDOM_SEED = 42

# Map Kaggle "usage" values onto a simple formality_level string.
USAGE_TO_FORMALITY = {
    "Casual": "casual",
    "Smart Casual": "smart-casual",
    "Formal": "formal",
    "Party": "party",
    "Ethnic": "ethnic",
    "Sports": "sport",
    "Travel": "casual",
    "Home": "casual",
    "NA": "casual",
}


def find_metadata_file() -> Path:
    """Prefer raw_dataset/ if it has a CSV/JSON; otherwise use data/raw/styles.csv."""
    raw_dataset = BACKEND_DIR / "data" / "raw_dataset"
    if raw_dataset.exists():
        candidates = list(raw_dataset.glob("*.csv")) + list(raw_dataset.glob("*.json"))
        if candidates:
            return candidates[0]
    if STYLES_CSV.exists():
        return STYLES_CSV
    raise FileNotFoundError(
        f"No metadata CSV/JSON found in {raw_dataset} or {STYLES_CSV}"
    )


def load_rows(path: Path) -> list[dict]:
    """Load CSV or JSON metadata and print the columns so you can verify them."""
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []
            print(f"Reading: {path}")
            print(f"Columns found ({len(columns)}): {columns}")
            rows = list(reader)
    elif path.suffix.lower() == ".json":
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            # Some dumps wrap the list under a key — take the first list value.
            rows = next((v for v in data.values() if isinstance(v, list)), [])
        else:
            rows = data
        columns = sorted({k for row in rows for k in row.keys()}) if rows else []
        print(f"Reading: {path}")
        print(f"Columns found ({len(columns)}): {columns}")
    else:
        raise ValueError(f"Unsupported metadata format: {path}")

    print(f"Total rows in source: {len(rows)}")
    return rows


def image_exists(item_id: str) -> bool:
    return (IMAGES_DIR / f"{item_id}.jpg").exists()


def normalize_row(row: dict) -> dict | None:
    """
    Convert one Kaggle styles.csv row into our Outfit-shaped dict.

    Field mapping (Kaggle → ours):
      - id                → local image path under data/raw/images/{id}.jpg
      - subCategory       → category (Topwear, Bottomwear, Shoes, … — good for diversity)
      - articleType       → included in style_tags for finer detail
      - usage / season / gender / articleType → style_tags (list)
      - usage             → formality_level (via USAGE_TO_FORMALITY)
      - baseColour        → color_tags (list)
    """
    item_id = (row.get("id") or "").strip()
    if not item_id or not image_exists(item_id):
        return None

    # v1 swipe deck: clothing + closed shoes (skip bags, watches, flip-flops, etc.)
    master = (row.get("masterCategory") or "").strip()
    if master not in {"Apparel", "Footwear"}:
        return None

    sub = (row.get("subCategory") or "").strip()
    # Skip categories that are a poor fit for outfit recommendations.
    if sub in {
        "Innerwear",
        "Loungewear and Nightwear",
        "Socks",
        "Apparel Set",
        "Saree",
        "Free Gifts",
        "Flip Flops",
        "Sandal",
    }:
        return None

    article = (row.get("articleType") or "").strip()
    usage = (row.get("usage") or "Casual").strip() or "Casual"
    color = (row.get("baseColour") or "").strip()
    season = (row.get("season") or "").strip()
    gender = (row.get("gender") or "").strip()

    # category = subCategory so stratified sampling spreads across Topwear/Bottomwear/Shoes
    category = sub or article or "Unknown"

    style_tags: list[str] = []
    for tag in (article, usage, season, gender):
        if tag and tag not in style_tags and tag != "NA":
            style_tags.append(tag)

    return {
        "image_url": f"data/raw/images/{item_id}.jpg",
        "category": category,
        "style_tags": style_tags,
        "formality_level": USAGE_TO_FORMALITY.get(usage, "casual"),
        "color_tags": [color] if color else [],
        # Keep source id for debugging; not stored on Outfit model.
        "source_id": item_id,
    }


def sample_diverse(items: list[dict], target: int) -> list[dict]:
    """
    Stratified sample by category so we don't just take the first N rows
    (which are often dominated by one article type like Tshirts).
    """
    by_category: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        by_category[item["category"]].append(item)

    rng = random.Random(RANDOM_SEED)
    for bucket in by_category.values():
        rng.shuffle(bucket)

    categories = sorted(by_category.keys())
    if not categories:
        return []

    # Round-robin: pull one item from each category until we hit target.
    selected: list[dict] = []
    index = 0
    while len(selected) < target:
        progressed = False
        for cat in categories:
            bucket = by_category[cat]
            if index < len(bucket):
                selected.append(bucket[index])
                progressed = True
                if len(selected) >= target:
                    break
        if not progressed:
            break
        index += 1

    rng.shuffle(selected)
    return selected


def main() -> None:
    metadata_path = find_metadata_file()
    rows = load_rows(metadata_path)

    normalized: list[dict] = []
    skipped_no_image = 0
    skipped_category = 0
    for row in rows:
        item = normalize_row(row)
        if item is None:
            # Distinguish missing image vs filtered masterCategory when possible.
            item_id = (row.get("id") or "").strip()
            master = (row.get("masterCategory") or "").strip()
            if item_id and not image_exists(item_id):
                skipped_no_image += 1
            elif master not in {"Apparel", "Footwear"}:
                skipped_category += 1
            else:
                skipped_category += 1
            continue
        normalized.append(item)

    print(f"Normalized candidates: {len(normalized)}")
    print(f"Skipped (no image): {skipped_no_image}")
    print(f"Skipped (non-clothing masterCategory): {skipped_category}")

    selected = sample_diverse(normalized, TARGET_COUNT)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(selected, f, indent=2)

    breakdown = Counter(item["category"] for item in selected)
    print()
    print(f"Wrote {len(selected)} items → {OUTPUT_JSON}")
    print("Category breakdown:")
    for cat, count in breakdown.most_common():
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
