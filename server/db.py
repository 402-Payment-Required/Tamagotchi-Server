import datetime
import os

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    con = get_conn()
    c = con.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS users("
        "user_id TEXT PRIMARY KEY, character TEXT DEFAULT 'grandson', created_at TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS signals("
        "id SERIAL PRIMARY KEY, user_id TEXT, type TEXT, value TEXT, ts TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS mission_progress("
        "id SERIAL PRIMARY KEY, user_id TEXT, mission_id TEXT, "
        "status TEXT, current_step INTEGER DEFAULT 0, completed_at TEXT, "
        "UNIQUE(user_id, mission_id))"
    )
    con.commit()
    con.close()


def ensure_user(user_id: str):
    con = get_conn()
    c = con.cursor()
    c.execute(
        "INSERT INTO users(user_id, created_at) VALUES(%s,%s) ON CONFLICT DO NOTHING",
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
            "INSERT INTO signals(user_id, type, value, ts) VALUES(%s,%s,%s,%s)",
            (user_id, k, str(v), now),
        )
    con.commit()
    con.close()


def get_progress(user_id: str, mission_id: str):
    con = get_conn()
    c = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute(
        "SELECT * FROM mission_progress WHERE user_id=%s AND mission_id=%s",
        (user_id, mission_id),
    )
    row = c.fetchone()
    con.close()
    return dict(row) if row else None


def list_progress(user_id: str):
    con = get_conn()
    c = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute(
        "SELECT * FROM mission_progress WHERE user_id=%s", (user_id,)
    )
    rows = c.fetchall()
    con.close()
    return {r["mission_id"]: dict(r) for r in rows}


def upsert_progress(user_id: str, mission_id: str, status: str, current_step: int):
    con = get_conn()
    c = con.cursor()
    now = datetime.datetime.now().isoformat()
    completed_at = now if status == "done" else None
    c.execute(
        """
        INSERT INTO mission_progress(user_id, mission_id, status, current_step, completed_at)
        VALUES(%s,%s,%s,%s,%s)
        ON CONFLICT(user_id, mission_id) DO UPDATE SET
            status=EXCLUDED.status,
            current_step=EXCLUDED.current_step,
            completed_at=EXCLUDED.completed_at
        """,
        (user_id, mission_id, status, current_step, completed_at),
    )
    con.commit()
    con.close()
