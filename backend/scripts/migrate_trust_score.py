"""
migrate_trust_score.py
=========================
One-time, idempotent migration: adds the `trust_score` / `trust_label`
columns to the existing `scan_results` table (Feature 4 — Trust Score
badge). Safe to run multiple times; skips columns that already exist.

Usage (from backend/):
    python -m scripts.migrate_trust_score
"""
import sqlite3

from app.config import DATABASE_URL

_DB_PATH = DATABASE_URL.replace("sqlite:///", "", 1)


def _column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def main() -> None:
    conn = sqlite3.connect(_DB_PATH)
    cur = conn.cursor()

    added = []
    if not _column_exists(cur, "scan_results", "trust_score"):
        cur.execute("ALTER TABLE scan_results ADD COLUMN trust_score FLOAT")
        added.append("trust_score")
    if not _column_exists(cur, "scan_results", "trust_label"):
        cur.execute("ALTER TABLE scan_results ADD COLUMN trust_label VARCHAR(16)")
        added.append("trust_label")

    conn.commit()
    conn.close()

    if added:
        print(f"Migration applied — added columns: {', '.join(added)}")
    else:
        print("No migration needed — columns already present.")


if __name__ == "__main__":
    main()