import sqlite3
from pathlib import Path
from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL UNIQUE,
    title TEXT DEFAULT '',
    authors TEXT DEFAULT '',
    year INTEGER,
    venue TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    read INTEGER DEFAULT 0,
    note TEXT DEFAULT '',
    bibtex TEXT DEFAULT '',
    date_added TEXT DEFAULT '',
    page_count INTEGER DEFAULT 0,
    file_size INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS speed_reads (
    paper_id TEXT PRIMARY KEY REFERENCES papers(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending',
    one_sentence TEXT DEFAULT '',
    quick_takeaways TEXT DEFAULT '[]',
    problem_and_motivation TEXT DEFAULT '',
    method_overview TEXT DEFAULT '',
    method_steps TEXT DEFAULT '[]',
    core_figures TEXT DEFAULT '[]',
    experiment_read TEXT DEFAULT '',
    contributions TEXT DEFAULT '[]',
    limitations TEXT DEFAULT '[]',
    deep_read_suggestions TEXT DEFAULT '[]',
    model_used TEXT DEFAULT '',
    tokens_used INTEGER DEFAULT 0,
    error_message TEXT DEFAULT '',
    generated_at TEXT DEFAULT ''
);

CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
    title, authors, venue, note,
    content='papers',
    content_rowid='rowid'
);

CREATE TABLE IF NOT EXISTS recycle_bin (
    id TEXT PRIMARY KEY,
    original_path TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    deleted_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 保持 FTS 索引同步的触发器
CREATE TRIGGER IF NOT EXISTS papers_ai AFTER INSERT ON papers BEGIN
    INSERT INTO papers_fts(rowid, title, authors, venue, note)
    VALUES (new.rowid, new.title, new.authors, new.venue, new.note);
END;

CREATE TRIGGER IF NOT EXISTS papers_ad AFTER DELETE ON papers BEGIN
    INSERT INTO papers_fts(papers_fts, rowid, title, authors, venue, note)
    VALUES ('delete', old.rowid, old.title, old.authors, old.venue, old.note);
END;

CREATE TRIGGER IF NOT EXISTS papers_au AFTER UPDATE ON papers BEGIN
    INSERT INTO papers_fts(papers_fts, rowid, title, authors, venue, note)
    VALUES ('delete', old.rowid, old.title, old.authors, old.venue, old.note);
    INSERT INTO papers_fts(rowid, title, authors, venue, note)
    VALUES (new.rowid, new.title, new.authors, new.venue, new.note);
END;
"""


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(settings.database_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
