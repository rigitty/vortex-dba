"""Database connection helper using pymssql for Microsoft SQL Server."""

import re
import pymssql

try:
    from src.config import get_config
except ImportError:
    from config import get_config


def get_connection(dbname: str | None = None, autocommit: bool = False, login_timeout: int = 2, timeout: int = 2):
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
            login_timeout=login_timeout,
            timeout=timeout,
            autocommit=autocommit,
        )
        return conn
    except Exception as e:
        err_str = str(e).lower()
        # Only try master if error indicates the specific database does not exist
        # If server itself is unreachable/connection refused/timed out, raise immediately without second timeout
        is_missing_db = ("does not exist" in err_str or "cannot open database" in err_str or "4060" in err_str)
        if database != "master" and is_missing_db:
            try:
                master_conn = pymssql.connect(
                    server=cfg.host,
                    port=str(cfg.port),
                    user=cfg.user,
                    password=cfg.password,
                    database="master",
                    login_timeout=login_timeout,
                    timeout=timeout,
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
                    login_timeout=login_timeout,
                    timeout=timeout,
                    autocommit=autocommit,
                )
            except Exception:
                pass
        raise



def ensure_database_exists() -> None:
    """Ensure the target database exists on SQL Server."""
    cfg = get_config().database
    try:
        conn = get_connection(dbname="master", autocommit=True, login_timeout=3, timeout=3)
        with conn.cursor() as cur:
            cur.execute(f"""
                IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{cfg.dbname}')
                BEGIN
                    CREATE DATABASE [{cfg.dbname}];
                END
            """)
        conn.close()
    except Exception:
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


def test_connection(host: str, port: int, dbname: str, user: str, password: str, timeout: int = 3) -> dict:
    """Test connection to a specific SQL Server database without changing global config."""
    try:
        conn = pymssql.connect(
            server=host.strip(),
            port=str(port).strip(),
            user=user.strip(),
            password=password,
            database=dbname.strip(),
            login_timeout=timeout,
            timeout=timeout,
            autocommit=True,
        )
        version_info = "Microsoft SQL Server"
        db_name_actual = dbname
        table_count = 0
        with conn.cursor(as_dict=True) as cur:
            cur.execute("SELECT @@VERSION AS ver, DB_NAME() AS db")
            row = cur.fetchone()
            if row:
                version_info = row.get("ver", "").split("\n")[0].strip()
                db_name_actual = row.get("db", dbname)
            
            try:
                cur.execute("SELECT COUNT(*) AS tbl_count FROM sys.tables WHERE is_ms_shipped = 0")
                tbl_row = cur.fetchone()
                if tbl_row:
                    table_count = tbl_row.get("tbl_count", 0)
            except Exception:
                pass

        conn.close()
        return {
            "success": True,
            "server_version": version_info,
            "database": db_name_actual,
            "table_count": table_count,
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


def check_current_connection(timeout: int = 2) -> dict:
    """Check connectivity to currently configured database in config.yaml."""
    cfg = get_config().database
    return test_connection(
        host=cfg.host,
        port=cfg.port,
        dbname=cfg.dbname,
        user=cfg.user,
        password=cfg.password,
        timeout=timeout,
    )


def apply_schema_script(script_path: str | None = None) -> tuple[bool, str]:
    """Execute initial schema script to create customers/orders tables and base indexes."""
    import os
    from pathlib import Path

    if script_path is None:
        # Default path init-scripts/01_schema.sql
        possible_paths = [
            Path(__file__).parent.parent / "init-scripts" / "01_schema.sql",
            Path(__file__).parent / "init-scripts" / "01_schema.sql",
            Path.cwd() / "init-scripts" / "01_schema.sql",
        ]
        for p in possible_paths:
            if p.exists():
                script_path = str(p)
                break

    if not script_path or not os.path.exists(script_path):
        return False, f"Şema dosyası (01_schema.sql) bulunamadı: {script_path}"

    try:
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
        execute_script(content)
        return True, "Şema ve tablolar (customers, orders) başarıyla oluşturuldu."
    except Exception as e:
        return False, f"Şema oluşturma hatası: {str(e)}"


