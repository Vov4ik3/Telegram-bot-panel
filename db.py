"""
SQLite storage for registered bots. One row per bot, keyed by an internal
auto-increment id. display_name is what you see and can rename in the UI;
static_name is just a record of what the bot's own manifest calls itself.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "panel.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    static_name TEXT NOT NULL,
    display_name TEXT NOT NULL UNIQUE,
    folder_path TEXT NOT NULL,
    entrypoint TEXT NOT NULL,
    venv_dir TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'offline',
    last_error TEXT
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute(SCHEMA)


def list_bots():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM bots ORDER BY display_name").fetchall()
        return [dict(r) for r in rows]


def get_bot(bot_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM bots WHERE id = ?", (bot_id,)).fetchone()
        return dict(row) if row else None


def display_name_taken(display_name, exclude_id=None):
    with get_conn() as conn:
        if exclude_id is None:
            row = conn.execute(
                "SELECT 1 FROM bots WHERE display_name = ?", (display_name,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT 1 FROM bots WHERE display_name = ? AND id != ?",
                (display_name, exclude_id),
            ).fetchone()
        return row is not None


def add_bot(static_name, display_name, folder_path, entrypoint, venv_dir, description):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO bots
               (static_name, display_name, folder_path, entrypoint, venv_dir, description, status)
               VALUES (?, ?, ?, ?, ?, ?, 'offline')""",
            (static_name, display_name, folder_path, entrypoint, venv_dir, description),
        )
        return cur.lastrowid


def rename_bot(bot_id, new_display_name):
    with get_conn() as conn:
        conn.execute(
            "UPDATE bots SET display_name = ? WHERE id = ?", (new_display_name, bot_id)
        )


def update_status(bot_id, status, last_error=None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE bots SET status = ?, last_error = ? WHERE id = ?",
            (status, last_error, bot_id),
        )


def delete_bot(bot_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
