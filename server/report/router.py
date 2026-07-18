import psycopg2.extras

from fastapi import APIRouter

from db import get_conn

router = APIRouter()


@router.get("/report")
def report(user_id: str):
    con = get_conn()
    c = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute(
        "SELECT type, value, ts FROM signals WHERE user_id=%s ORDER BY ts DESC LIMIT 20",
        (user_id,),
    )
    rows = c.fetchall()
    con.close()
    return {"user_id": user_id, "signals": [dict(r) for r in rows]}
