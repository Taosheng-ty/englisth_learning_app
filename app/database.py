import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    ui_language TEXT NOT NULL DEFAULT 'zh',
    daily_goal INTEGER NOT NULL DEFAULT 5,
    tts_speed REAL NOT NULL DEFAULT 1.0,
    xp INTEGER NOT NULL DEFAULT 0,
    streak_days INTEGER NOT NULL DEFAULT 0,
    last_practice_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    title_zh TEXT NOT NULL,
    title_vi TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    category TEXT NOT NULL,
    sentence_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sentences (
    id TEXT PRIMARY KEY,
    lesson_id INTEGER NOT NULL REFERENCES lessons(id),
    idx INTEGER NOT NULL,
    text TEXT NOT NULL,
    translation_zh TEXT NOT NULL,
    translation_vi TEXT NOT NULL,
    words_json TEXT NOT NULL,
    constituents_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    sentence_id TEXT NOT NULL REFERENCES sentences(id),
    mode TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0.0,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt TIMESTAMP,
    next_review TIMESTAMP,
    leitner_bucket INTEGER NOT NULL DEFAULT 1,
    UNIQUE(user_id, sentence_id, mode)
);

CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    word TEXT NOT NULL,
    ipa TEXT,
    pos TEXT,
    seen_count INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    next_review TIMESTAMP,
    UNIQUE(user_id, word)
);
"""


def init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_db_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
