"""SQLite client singleton for Growth OS.

Replaces the former Supabase client.  Provides a module-level connection
singleton, schema initialisation, and helpers.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH: str = os.getenv(
    "SQLITE_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "growth.db"),
)

_db_connection: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    """Return (and lazily initialise) the SQLite connection singleton."""
    global _db_connection
    if _db_connection is not None:
        return _db_connection

    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    os.makedirs(db_dir, exist_ok=True)

    _db_connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    _db_connection.row_factory = sqlite3.Row
    _db_connection.execute("PRAGMA journal_mode=WAL")
    _db_connection.execute("PRAGMA foreign_keys=ON")
    logger.info("SQLite connected: %s", os.path.abspath(DB_PATH))
    return _db_connection


def close_connection() -> None:
    """Close the cached connection."""
    global _db_connection
    if _db_connection:
        _db_connection.close()
        _db_connection = None
        logger.info("SQLite connection closed")


def reset_client() -> None:
    """Reset the cached connection (useful for tests). Alias for close_connection."""
    close_connection()


def init_schema() -> None:
    """Initialize database schema from the SQLite SQL file."""
    conn = get_connection()
    sql_dir = Path(__file__).resolve().parent.parent.parent.parent / "sql"
    schema_file = sql_dir / "001_init_schema_sqlite.sql"
    if schema_file.exists():
        sql = schema_file.read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.commit()
        logger.info("Schema initialized from %s", schema_file)
    else:
        logger.warning("Schema file not found: %s", schema_file)


def get_client():  # backward-compat shim
    """Return the connection – kept for any callers that imported get_client."""
    return get_connection()
