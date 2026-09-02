"""Database connection helper using pymssql for Microsoft SQL Server."""

import re
import pymssql

from config import get_config


def get_connection(dbname: str | None = None, autocommit: bool = False):
    """Create and return a new SQL Server database connection."""
    cfg = get_config().database
    database = dbname if dbname is not None else cfg.dbname
    try:
        conn = pymssql.connect(
            server=cfg.host,
            port=str(cfg.port),
            user=cfg.user,
            password=cfg.password,
            database=database,
            autocommit=autocommit,
        )
        return conn
    except Exception:
        if database != "master":
            try:
                master_conn = pymssql.connect(
                    server=cfg.host,
                    port=str(cfg.port),
                    user=cfg.user,
                    password=cfg.password,
                    database="master",
                    autocommit=True,
                )
                with master_conn.cursor() as cur:
                    cur.execute(f"""
                        IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{cfg.dbname}')
                        BEGIN
                            CREATE DATABASE [{cfg.dbname}];
                        END
                    """)
                master_conn.close()
                return pymssql.connect(
                    server=cfg.host,
                    port=str(cfg.port),
                    user=cfg.user,
                    password=cfg.password,
                    database=database,
                    autocommit=autocommit,
                )
            except Exception:
                pass
        raise


def ensure_database_exists() -> None:
    """Ensure the target database exists on SQL Server."""
    cfg = get_config().database
    try:
        conn = get_connection(dbname="master", autocommit=True)
        with conn.cursor() as cur:
            cur.execute(f"""
                IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{cfg.dbname}')
                BEGIN
                    CREATE DATABASE [{cfg.dbname}];
                END
            """)
        conn.close()
    except Exception as e:
        # Ignore if cannot connect to master or already exists
        pass


def execute_query(query: str, params: tuple | None = None, fetch: bool = True, autocommit: bool = False) -> list[dict] | None:
    """Execute a query and optionally return results as list of dicts."""
    conn = get_connection(autocommit=autocommit)
    try:
        with conn.cursor(as_dict=True) as cur:
            cur.execute(query, params)
            if fetch and cur.description:
                return cur.fetchall()
            if not autocommit:
                conn.commit()
            return None
    finally:
        conn.close()


def execute_script(script: str) -> None:
    """Execute a multi-statement T-SQL script handling GO batch separators."""
    conn = get_connection(autocommit=True)
    try:
        # Split script by GO batch separator
        batches = re.split(r'^\s*GO\s*$', script, flags=re.MULTILINE | re.IGNORECASE)
        with conn.cursor() as cur:
            for batch in batches:
                clean_batch = batch.strip()
                if clean_batch:
                    cur.execute(clean_batch)
    finally:
        conn.close()


def test_connection(host: str, port: int, dbname: str, user: str, password: str) -> dict:
    """Test connection to a specific SQL Server database without changing global config."""
    try:
        conn = pymssql.connect(
            server=host.strip(),
            port=str(port).strip(),
            user=user.strip(),
            password=password,
            database=dbname.strip(),
            login_timeout=5,
            timeout=5,
            autocommit=True,
        )
        version_info = "Microsoft SQL Server"
        db_name_actual = dbname
        with conn.cursor(as_dict=True) as cur:
            cur.execute("SELECT @@VERSION AS ver, DB_NAME() AS db")
            row = cur.fetchone()
            if row:
                version_info = row.get("ver", "").split("\n")[0].strip()
                db_name_actual = row.get("db", dbname)
        conn.close()
        return {
            "success": True,
            "server_version": version_info,
            "database": db_name_actual,
            "host": host.strip(),
            "port": int(port),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "host": host.strip(),
            "port": int(port),
            "database": dbname.strip(),
        }

