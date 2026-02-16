import sqlite3
import os
from collections.abc import Generator

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "party.db")


def connect_to_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db() -> Generator[sqlite3.Connection]:
    """
    Provides a database connection for the duration of a request.
    The connection is automatically closed after the request is processed.
    """
    conn = connect_to_db()
    try:
        yield conn
    finally:
        conn.close()


def get_competition_status(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'competition_status'"
    ).fetchone()
    return row["value"] if row else "setup"


def init_db():
    conn = connect_to_db()  # Ensure the database file is created if it doesn't exist
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            access_code TEXT UNIQUE NOT NULL,
            display_name TEXT,
            dressed_up_as TEXT,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS costumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
            photo_filename TEXT NOT NULL,
            upload_timestamp TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id INTEGER NOT NULL REFERENCES users(id),
            costume_id INTEGER NOT NULL REFERENCES costumes(id),
            timestamp TEXT DEFAULT (datetime('now')),
            UNIQUE(voter_id, costume_id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        INSERT OR IGNORE INTO settings (key, value) VALUES ('competition_status', 'setup');
    """)
    conn.commit()
    conn.close()
