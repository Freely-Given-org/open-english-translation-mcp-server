#!/usr/bin/env python3
"""
scripts/verify_db.py

Validates that the OET corpus SQLite database is a real, queryable database
with the expected schema and non-empty tables.

Used as a build-time guard in the Docker image: if a checkout was made without
Git-LFS (`git lfs pull`), the 191 MB corpus DB is only a ~130-byte LFS pointer
file and every data tool fails at runtime. This script makes that failure
happen at `docker build` time instead of silently shipping a broken image.

Usage:
    python3 scripts/verify_db.py [path-to-oet_corpus.db]
"""

import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = (
    Path(__file__).resolve().parent.parent
    / "src" / "oet_mcp_server" / "data" / "oet_corpus.db"
)

REQUIRED_TABLES = {"books", "verses", "words", "lexicon"}


def check(db_path=None):
    """Return True if the DB is valid; print diagnostic info. No side effects."""
    db_path = Path(db_path) if db_path else DEFAULT_DB
    if not db_path.exists():
        print(f"FAIL: DB not found at {db_path}", file=sys.stderr)
        print("      (Was `git lfs pull` run before the build?)", file=sys.stderr)
        return False

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error as e:
        print(f"FAIL: cannot open DB at {db_path}: {e}", file=sys.stderr)
        print("      The file exists but is not a valid SQLite database.", file=sys.stderr)
        return False

    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        missing = sorted(REQUIRED_TABLES - tables)
        if missing:
            print(f"FAIL: DB at {db_path} is missing table(s): {', '.join(missing)}",
                  file=sys.stderr)
            return False

        verses = conn.execute("SELECT count(*) FROM verses").fetchone()[0]
        words = conn.execute("SELECT count(*) FROM words").fetchone()[0]
        if verses <= 0 or words <= 0:
            print(f"FAIL: DB at {db_path} has empty tables (verses={verses}, words={words})",
                  file=sys.stderr)
            return False

        print(f"OK: {db_path} ({db_path.stat().st_size:,} bytes, "
              f"{verses:,} verses, {words:,} words)")
        return True
    except sqlite3.Error as e:
        print(f"FAIL: error querying DB at {db_path}: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(0 if check(path) else 1)