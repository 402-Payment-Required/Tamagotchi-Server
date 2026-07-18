import sqlite3

from fastapi import APIRouter

from db import get_conn

router = APIRouter()


@router.get("/report")
def report(user_id: str):
    con = get_conn()
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT type, value, ts FROM signals WHERE user_id=? ORDER BY ts DESC LIMIT 20",
        (user_id,),
    ).fetchall()
    con.close()
    return {"user_id": user_id, "signals": [dict(r) for r in rows]}
