"""SQLite connection handling.

The DB lives OUTSIDE the Dropbox-synced repo by default (~/alps-data/alps.db):
SQLite WAL files inside an actively-syncing Dropbox folder risk corruption.
Override with the ALPS_DB env var.
"""

import os
import sqlite3
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent.parent
DEFAULT_DB = Path.home() / "alps-data" / "alps.db"


def db_path() -> Path:
    return Path(os.environ.get("ALPS_DB", DEFAULT_DB))


def connect(create: bool = False) -> sqlite3.Connection:
    path = db_path()
    if not create and not path.exists():
        raise SystemExit(f"Database not found at {path}. Run `alpsfinder init-db` first.")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db() -> Path:
    conn = connect(create=True)
    schema = (PACKAGE_DIR / "schema.sql").read_text()
    conn.executescript(schema)
    conn.commit()
    conn.close()
    return db_path()
