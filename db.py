"""
Tiny SQLite layer used for two things only:
1. Remembering which articles we've already covered (dedup).
2. Recording what got posted where, for a simple history/audit trail.

Deliberately kept dependency-free (stdlib sqlite3) and separate from
any database your main SaaS app uses.
"""
import sqlite3
import hashlib
import time
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT UNIQUE NOT NULL,
    source_title TEXT,
    source_url TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    fingerprint TEXT,
    blog_posted INTEGER DEFAULT 0,
    telegram_posted INTEGER DEFAULT 0,
    whatsapp_posted INTEGER DEFAULT 0,
    x_posted INTEGER DEFAULT 0,
    created_at REAL NOT NULL
);
"""


@contextmanager
def _conn():
    conn = sqlite3.connect(config.DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as conn:
        conn.executescript(SCHEMA)


def fingerprint_for(title: str, url: str = "") -> str:
    """Stable hash used to detect the same story even if wording differs slightly."""
    key = (url or title).strip().lower()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def is_duplicate(title: str, url: str = "") -> bool:
    fp = fingerprint_for(title, url)
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM seen_articles WHERE fingerprint = ?", (fp,)
        ).fetchone()
    return row is not None


def mark_seen(title: str, url: str = ""):
    fp = fingerprint_for(title, url)
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_articles (fingerprint, source_title, source_url, created_at) "
            "VALUES (?, ?, ?, ?)",
            (fp, title, url, time.time()),
        )


def record_post_result(title: str, fingerprint: str, channel: str, success: bool):
    """channel is one of: blog, telegram, whatsapp, x"""
    column = f"{channel}_posted"
    assert column in (
        "blog_posted",
        "telegram_posted",
        "whatsapp_posted",
        "x_posted",
    ), f"unknown channel {channel}"

    with _conn() as conn:
        row = conn.execute(
            "SELECT id FROM posts WHERE fingerprint = ?", (fingerprint,)
        ).fetchone()
        if row is None:
            conn.execute(
                f"INSERT INTO posts (title, fingerprint, {column}, created_at) VALUES (?, ?, ?, ?)",
                (title, fingerprint, int(success), time.time()),
            )
        else:
            conn.execute(
                f"UPDATE posts SET {column} = ? WHERE fingerprint = ?",
                (int(success), fingerprint),
            )
