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
    try:
        conn.executescript(SCHEMA)
        conn.execute("BEGIN IMMEDIATE")
        # 兼容已有论文库，保留所有手工编辑和速读结果。
        columns = {r[1] for r in conn.execute("PRAGMA table_info(papers)")}
        for name, definition in {
            "content_hash": "TEXT DEFAULT ''",
            "file_mtime_ns": "INTEGER DEFAULT 0",
            "file_missing": "INTEGER DEFAULT 0",
        }.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE papers ADD COLUMN {name} {definition}")
        conn.execute("CREATE TABLE IF NOT EXISTS library_state (id INTEGER PRIMARY KEY, revision INTEGER NOT NULL DEFAULT 0)")
        conn.execute("INSERT OR IGNORE INTO library_state (id, revision) VALUES (1, 0)")
        for table in ("papers", "speed_reads"):
            for action in ("INSERT", "UPDATE", "DELETE"):
                conn.execute(f"""CREATE TRIGGER IF NOT EXISTS revision_{table}_{action}
                    AFTER {action} ON {table} BEGIN
                    UPDATE library_state SET revision = revision + 1 WHERE id = 1;
                    END""")
        conn.commit()
    finally:
        conn.close()
