from fastapi import APIRouter
from ..db.db import init_db, connect

router = APIRouter()
@router.get("/health")
def healthcheck() -> int:
    init_db()

    with connect() as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [r["name"] for r in cur.fetchall()]

    print(f"DB OK. Tables: {', '.join(tables)}")
    return 0