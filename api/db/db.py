import sqlite3
import os
from pathlib import Path
from .schema import apply_schema
from dotenv import load_dotenv
load_dotenv()

def connect() -> sqlite3.Connection:
    raw_db_path = os.getenv("DB_PATH", "").strip()
    if not raw_db_path:
        raise RuntimeError("DB_PATH is not set")

    db_path = Path(raw_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(db_path),
        timeout=30.0,
        detect_types=sqlite3.PARSE_DECLTYPES,
    )
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA wal_autocheckpoint=1000;")

    return conn

def init_db() -> None:
    with connect() as conn:
        apply_schema(conn)