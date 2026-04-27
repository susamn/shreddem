import sqlite3
import logging
import threading
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "shreddem"
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
    except Exception as e:
        logger.error("Failed to clear database: %s", e)

def insert_emails(emails):
    """Insert or replace a list of EmailHeader objects into the database."""
    with get_connection() as conn:
        try:
            conn.execute("BEGIN TRANSACTION")
            for em in emails:
                if hasattr(em, "uid"):
                    # EmailHeader dataclass
                    conn.execute(
                        "INSERT OR REPLACE INTO emails (uid, subject, sender_email, sender_name, date, timestamp, is_read, snippet) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (em.uid, em.subject, em.sender_email, em.sender_name, em.date, em.timestamp, int(em.is_read), getattr(em, "snippet", ""))
                    )
                elif isinstance(em, dict):
                    conn.execute(
                        "INSERT OR REPLACE INTO emails (uid, subject, sender_email, sender_name, date, timestamp, is_read, snippet) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (em.get("uid"), em.get("subject", ""), em.get("sender_email", ""),
                         em.get("sender_name", ""), em.get("date", ""), em.get("timestamp", 0),
                         int(em.get("is_read", True)), em.get("snippet", ""))
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

@contextmanager
def get_connection():
    """Get a thread-local SQLite connection with dictionary row factory."""
    if not hasattr(_local, "conn"):
        # We use check_same_thread=False but strictly isolate objects via thread-local,
        # ensuring fast thread safety.
        # Added timeout to prevent "database is locked" errors with multiple workers.
        _local.conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)
        _local.conn.row_factory = dict_factory
        _local.conn.execute("PRAGMA synchronous = OFF")
        _local.conn.execute("PRAGMA journal_mode = WAL")
        _local.conn.execute("PRAGMA busy_timeout = 30000")

    try:
        yield _local.conn
    except Exception:
        _local.conn.rollback()
        raise

def dict_factory(cursor, row):
    """Dictionary factory for sqlite3 rows to convert them nicely."""
    d = {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
    # Re-map numeric boolean back to Python boolean for application layer
    if 'is_read' in d:
        d['is_read'] = bool(d['is_read'])
    return d
