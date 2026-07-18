import datetime
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "sonju.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    con = get_conn()
    c = con.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS users("
        "user_id TEXT PRIMARY KEY, character TEXT DEFAULT 'grandson', created_at TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS signals("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, type TEXT, value TEXT, ts TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS mission_progress("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, mission_id TEXT, "
        "status TEXT, current_step INTEGER DEFAULT 0, completed_at TEXT, "
        "UNIQUE(user_id, mission_id))"
    )
    con.commit()
    con.close()


def ensure_user(user_id: str):
    con = get_conn()
    c = con.cursor()
    c.execute(
        "INSERT OR IGNORE INTO users(user_id, created_at) VALUES(?,?)",
        (user_id, datetime.datetime.now().isoformat()),
    )
    con.commit()
    con.close()


def save_signals(user_id: str, signals: dict):
    con = get_conn()
    c = con.cursor()
    now = datetime.datetime.now().isoformat()
    for k, v in signals.items():
        c.execute(
            "INSERT INTO signals(user_id, type, value, ts) VALUES(?,?,?,?)",
            (user_id, k, str(v), now),
        )
    con.commit()
    con.close()


def get_progress(user_id: str, mission_id: str):
    con = get_conn()
    con.row_factory = sqlite3.Row
    row = con.execute(
        "SELECT * FROM mission_progress WHERE user_id=? AND mission_id=?",
        (user_id, mission_id),
    ).fetchone()
    con.close()
    return dict(row) if row else None


def list_progress(user_id: str):
    con = get_conn()
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM mission_progress WHERE user_id=?", (user_id,)
    ).fetchall()
    con.close()
    return {r["mission_id"]: dict(r) for r in rows}


def upsert_progress(user_id: str, mission_id: str, status: str, current_step: int):
    con = get_conn()
    now = datetime.datetime.now().isoformat()
    completed_at = now if status == "done" else None
    con.execute(
        """
        INSERT INTO mission_progress(user_id, mission_id, status, current_step, completed_at)
        VALUES(?,?,?,?,?)
        ON CONFLICT(user_id, mission_id) DO UPDATE SET
            status=excluded.status,
            current_step=excluded.current_step,
            completed_at=excluded.completed_at
        """,
        (user_id, mission_id, status, current_step, completed_at),
    )
    con.commit()
    con.close()
