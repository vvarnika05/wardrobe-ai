"""
migrate_add_gender.py
---------------------
create_all() will not ALTER existing tables. This adds:
  - outfits.gender        (nullable TEXT) — Kaggle catalog department
  - profiles.gender_pref  (nullable TEXT) — clothing filter: men|women|unisex

Usage (from backend/):
    python scripts/migrate_add_gender.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine


def main() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE outfits
                ADD COLUMN IF NOT EXISTS gender VARCHAR
                """
            )
        )
        print("Ensured outfits.gender exists")

        # Index helps Postgres filters; IF NOT EXISTS needs PG 9.5+ (fine on Supabase).
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_outfits_gender
                ON outfits (gender)
                """
            )
        )
        print("Ensured ix_outfits_gender exists")

        conn.execute(
            text(
                """
                ALTER TABLE profiles
                ADD COLUMN IF NOT EXISTS gender_pref VARCHAR
                """
            )
        )
        print("Ensured profiles.gender_pref exists")

    print("Migration complete.")


if __name__ == "__main__":
    main()
