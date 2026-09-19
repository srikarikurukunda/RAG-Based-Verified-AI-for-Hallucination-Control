import sqlite3, os, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# This file lives in backend/, so its parent's parent is the project root.
# SQLITE_DB_PATH in .env is a relative path written against the project
# root -- resolve it against BASE_DIR rather than the process's current
# working directory (see rag_retriever.py for the full explanation).
BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve(path_str: str) -> str:
    p = Path(path_str)
    return str(p if p.is_absolute() else BASE_DIR / p)


DB_PATH = _resolve(os.getenv("SQLITE_DB_PATH", "answers.db"))


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            question_hash TEXT PRIMARY KEY,
            answer        TEXT NOT NULL,
            sources       TEXT,
            index_version TEXT,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    # Lightweight migration for databases created before sources/index_version
    # existed, so older answers.db files don't break on upgrade.
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(answers)")}
    if "sources" not in existing_cols:
        conn.execute("ALTER TABLE answers ADD COLUMN sources TEXT")
    if "index_version" not in existing_cols:
        conn.execute("ALTER TABLE answers ADD COLUMN index_version TEXT")
    return conn


def get_cached(question_hash: str):
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT answer, created_at, sources, index_version FROM answers WHERE question_hash=?",
            (question_hash,)).fetchone()
    if row:
        answer, created_at, sources_json, index_version = row
        try:
            sources = json.loads(sources_json) if sources_json else []
        except json.JSONDecodeError:
            sources = []
        return {
            "found": True,
            "answer": answer,
            "timestamp": created_at,
            "sources": sources,
            "index_version": index_version,
        }
    return {"found": False}


def store_cached(question_hash: str, answer: str, sources=None, index_version=None):
    # Upsert instead of INSERT OR IGNORE: a regenerated answer (e.g. after
    # the knowledge base changed) must actually overwrite a stale cached
    # row, not silently no-op because the hash already exists.
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO answers (question_hash, answer, sources, index_version)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(question_hash) DO UPDATE SET
                   answer=excluded.answer,
                   sources=excluded.sources,
                   index_version=excluded.index_version,
                   created_at=CURRENT_TIMESTAMP""",
            (question_hash, answer, json.dumps(sources or []), index_version))


def clear_cache():
    with _get_conn() as conn:
        conn.execute("DELETE FROM answers")
