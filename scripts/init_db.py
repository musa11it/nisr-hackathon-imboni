"""Initialise the configured database safely.

    python scripts/init_db.py

* Reads DATABASE_URL from .env (MySQL via PyMySQL, or SQLite).
* MySQL: runs CREATE DATABASE IF NOT EXISTS `<name>` (identifier validated and
  backtick-quoted) if DB_CREATE_DATABASE=true, then creates Imboni's own tables.
* Never creates users, grants privileges, changes passwords or drops databases.
* Mirrors the processed reference data into the observations/indicators/sources tables.
* Falls back to SQLite only if DB_FALLBACK_ENABLED=true, and says so.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.db import db_status, init_engine  # noqa: E402
from backend.app.main import seed_database  # noqa: E402
from backend.app.store import get_store  # noqa: E402


def main() -> int:
    init_engine()
    status = db_status()
    info = seed_database(get_store())
    print(f"Database backend : {status['backend']}")
    print(f"Connected        : {status['connected']}")
    if status["fallback_reason"]:
        print(f"Fallback reason  : {status['fallback_reason']}")
        print("-> MySQL was not used. See docs/DATABASE.md for the one-time setup a DBA must run.")
    print(f"Reference data   : {'seeded' if info['seeded'] else 'already up to date'} ({info['observations']} observations)")
    return 0 if status["connected"] else 1


if __name__ == "__main__":
    sys.exit(main())
