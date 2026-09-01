"""FastAPI web application for VortexDBA.

Provides a REST API and web dashboard for monitoring
PostgreSQL performance and managing the self-healing agent.
"""

import sys
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config
from state_store import init_db, get_active_indexes, get_recent_decisions, get_benchmark_history
from pg_stats_reader import get_table_stats, get_index_stats, get_top_queries_by_time
from unused_index_detector import get_unused_indexes, get_index_usage_stats
from safety_guard import get_safety_report

app = FastAPI(
    title="VortexDBA",
    description="Autonomous Database Performance Optimizer",
    version="1.0.0",
)

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    template = templates.get_template("dashboard.html")
    content = template.render(request=request)
    return HTMLResponse(content=content)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/stats")
async def api_stats():
    """Get PostgreSQL statistics."""
    try:
        table_stats = get_table_stats()
        index_stats = get_index_stats()
        top_queries = get_top_queries_by_time(5)

        return {
            "tables": [
                {
                    "name": s.relname,
                    "seq_scans": s.seq_scan,
                    "idx_scans": s.idx_scan,
                    "live_tuples": s.n_live_tup,
                    "dead_tuples": s.n_dead_tup,
                }
                for s in table_stats
            ],
            "indexes": [
                {
                    "table": s.relname,
                    "name": s.indexrelname,
                    "scans": s.idx_scan,
                    "tuples_read": s.idx_tup_read,
                }
                for s in index_stats
            ],
            "top_queries": [
                {
                    "query": q.query[:100],
                    "calls": q.calls,
                    "mean_ms": q.mean_exec_time,
                    "total_ms": q.total_exec_time,
                }
                for q in top_queries
            ],
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/indexes")
async def api_indexes():
    """Get active indexes from state store."""
    try:
        indexes = get_active_indexes()
        return {
            "indexes": [
                {
                    "name": idx.index_name,
                    "table": idx.table_name,
                    "columns": idx.columns,
                    "applied_at": idx.applied_at,
                    "reason": idx.reason,
                }
                for idx in indexes
            ]
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/unused-indexes")
async def api_unused_indexes():
    """Get unused indexes."""
    try:
        unused = get_unused_indexes()
        return {
            "unused_indexes": [
                {
                    "name": idx.index_name,
                    "table": idx.table_name,
                    "columns": idx.columns,
                    "size": idx.index_size_pretty,
                    "drop_statement": idx.drop_statement,
                }
                for idx in unused
            ],
            "total_reclaimable": sum(idx.index_size_bytes for idx in unused),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/decisions")
async def api_decisions():
    """Get recent agent decisions."""
    try:
        decisions = get_recent_decisions(20)
        return {
            "decisions": [
                {
                    "type": d.decision_type,
                    "details": d.details,
                    "timestamp": d.created_at,
                }
                for d in decisions
            ]
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/benchmark-history/{query_name}")
async def api_benchmark_history(query_name: str):
    """Get benchmark history for a query."""
    try:
        history = get_benchmark_history(query_name, 10)
        return {
            "query_name": query_name,
            "history": [
                {
                    "mean_ms": h.mean_ms,
                    "median_ms": h.median_ms,
                    "measured_at": h.measured_at,
                    "index_snapshot": h.index_snapshot,
                }
                for h in history
            ]
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/safety-report")
async def api_safety_report():
    """Get safety status report."""
    try:
        report = get_safety_report()
        return {"report": report}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/config")
async def api_config():
    """Get current configuration (non-sensitive)."""
    config = get_config()
    return {
        "detection": {
            "min_mean_exec_time_ms": config.detection.min_mean_exec_time_ms,
            "min_total_exec_time_ms": config.detection.min_total_exec_time_ms,
            "min_calls": config.detection.min_calls,
        },
        "remediation": {
            "enabled": config.remediation.enabled,
            "dry_run_default": config.remediation.dry_run_default,
            "max_indexes_per_table": config.remediation.max_indexes_per_table,
            "max_indexes_total": config.remediation.max_indexes_total,
            "cooldown_minutes": config.remediation.cooldown_minutes,
        },
        "benchmark": {
            "runs": config.benchmark.runs,
            "degradation_threshold_pct": config.benchmark.degradation_threshold_pct,
        },
    }
