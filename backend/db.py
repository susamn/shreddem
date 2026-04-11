import sqlite3
import os
import threading
from pathlib import Path
from contextlib import contextmanager

CONFIG_DIR = Path.home() / ".config" / "gmail-client"
DB_FILE = CONFIG_DIR / "emails.db"

# Thread-local storage for DB connections, since sqlite3 connections cannot be shared across threads.
_local = threading.local()

def get_db_path() -> Path:
    return DB_FILE

def init_db():
    """Ensure the database directory exists and initialize the schema."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                uid TEXT PRIMARY KEY,
                subject TEXT,
                sender_email TEXT,
                sender_name TEXT,
                date TEXT,
                timestamp REAL,
                is_read INTEGER,
                snippet TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sender_email ON emails(sender_email)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON emails(timestamp DESC)")
        conn.commit()

def clear_db():
    """Clear all data from the database securely on logout."""
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM emails")
            conn.commit()
            conn.execute("VACUUM")
    except Exception:
        pass

@contextmanager
def get_connection():
    """Get a thread-local SQLite connection with dictionary row factory."""
    if not hasattr(_local, "conn"):
        # We use check_same_thread=False but strictly isolate objects via thread-local,
        # ensuring fast thread safety.
        _local.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        _local.conn.row_factory = dict_factory
        _local.conn.execute("PRAGMA synchronous = OFF")
        _local.conn.execute("PRAGMA journal_mode = WAL")

    try:
        yield _local.conn
    except Exception:
        _local.conn.rollback()
        raise

def dict_factory(cursor, row):
    """Dictionary factory for sqlite3 rows to convert them nicely."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    # Re-map numeric boolean back to Python boolean for application layer
    if 'is_read' in d:
        d['is_read'] = bool(d['is_read'])
    return d
