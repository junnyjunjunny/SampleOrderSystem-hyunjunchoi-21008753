import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "samples.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    sample_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    avg_production_time REAL NOT NULL,
    yield_rate REAL NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    sample_id TEXT NOT NULL REFERENCES samples(sample_id),
    customer_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    production_quantity INTEGER,
    production_started_at TEXT,
    production_queue_seq INTEGER
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(orders)")}
    if "production_quantity" not in existing_columns:
        conn.execute("ALTER TABLE orders ADD COLUMN production_quantity INTEGER")
    if "production_started_at" not in existing_columns:
        conn.execute("ALTER TABLE orders ADD COLUMN production_started_at TEXT")
    if "production_queue_seq" not in existing_columns:
        conn.execute("ALTER TABLE orders ADD COLUMN production_queue_seq INTEGER")
    conn.commit()


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate(conn)
    return conn
