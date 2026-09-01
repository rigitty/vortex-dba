"""Database connection helper using psycopg2."""

import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "vortex_db",
    "user": "vortex_user",
    "password": "vortex_password",
}


def get_connection(autocommit: bool = False):
    """Create and return a new database connection."""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = autocommit
    return conn


def execute_query(query: str, params: tuple | None = None, fetch: bool = True) -> list[dict] | None:
    """Execute a query and optionally return results as list of dicts."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch and cur.description:
                return cur.fetchall()
            conn.commit()
            return None
    finally:
        conn.close()


def execute_script(script: str) -> None:
    """Execute a multi-statement SQL script."""
    conn = get_connection(autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(script)
    finally:
        conn.close()
