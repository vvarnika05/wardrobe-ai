"""
migrate_swipe_logs_unique.py
----------------------------
Our project uses Base.metadata.create_all() (no Alembic). create_all() will
NOT alter an existing swipe_logs table — it only creates missing tables.

This script applies the schema change to a live Postgres/Supabase DB:
  1. Delete duplicate (user_id, outfit_id) rows, keeping the newest
  2. Add updated_at column if missing
  3. Add UNIQUE (user_id, outfit_id) if missing

Usage (from backend/):
    python scripts/migrate_swipe_logs_unique.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine


def main() -> None:
    with engine.begin() as conn:
        # --- 1. Show duplicates (if any) ---
        dupes = conn.execute(
            text(
                """
                SELECT user_id, outfit_id, COUNT(*) AS n
                FROM swipe_logs
                GROUP BY user_id, outfit_id
                HAVING COUNT(*) > 1
                """
            )
        ).fetchall()
        print(f"Duplicate (user_id, outfit_id) pairs found: {len(dupes)}")

        # --- 2. Keep newest row per pair (highest id), delete the rest ---
        # Postgres DISTINCT ON keeps the first row per group after ORDER BY.
        deleted = conn.execute(
            text(
                """
                DELETE FROM swipe_logs
                WHERE id NOT IN (
                    SELECT DISTINCT ON (user_id, outfit_id) id
                    FROM swipe_logs
                    ORDER BY user_id, outfit_id, created_at DESC, id DESC
                )
                """
            )
        )
        print(f"Deleted older duplicate rows: {deleted.rowcount}")

        # --- 3. Add updated_at if the column does not exist yet ---
        conn.execute(
            text(
                """
                ALTER TABLE swipe_logs
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ
                    NOT NULL DEFAULT NOW()
                """
            )
        )
        # Backfill: for existing rows, treat last known time as updated_at.
        conn.execute(
            text(
                """
                UPDATE swipe_logs
                SET updated_at = created_at
                WHERE updated_at IS NULL
                   OR updated_at < created_at
                """
            )
        )
        print("Ensured updated_at column exists")

        # --- 4. Add unique constraint if missing ---
        exists = conn.execute(
            text(
                """
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_swipe_logs_user_outfit'
                """
            )
        ).scalar()
        if exists:
            print("Unique constraint uq_swipe_logs_user_outfit already exists")
        else:
            conn.execute(
                text(
                    """
                    ALTER TABLE swipe_logs
                    ADD CONSTRAINT uq_swipe_logs_user_outfit
                    UNIQUE (user_id, outfit_id)
                    """
                )
            )
            print("Added unique constraint uq_swipe_logs_user_outfit")

    print("Migration complete.")


if __name__ == "__main__":
    main()
