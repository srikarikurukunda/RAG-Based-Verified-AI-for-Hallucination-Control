import sqlite3, os
from dotenv import load_dotenv
load_dotenv()

DB_PATH = os.getenv("SQLITE_DB_PATH", "answers.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            question_hash TEXT PRIMARY KEY,
            answer        TEXT NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    return conn

def get_cached(question_hash: str):
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT answer, created_at FROM answers WHERE question_hash=?",
            (question_hash,)).fetchone()
    if row:
        return {"found": True, "answer": row[0], "timestamp": row[1]}
    return {"found": False}

def store_cached(question_hash: str, answer: str):
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO answers (question_hash, answer) VALUES (?,?)",
            (question_hash, answer))