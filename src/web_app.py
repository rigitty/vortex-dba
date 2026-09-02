"""FastAPI web application for VortexDBA.

Provides a REST API and web dashboard for monitoring
PostgreSQL performance and managing the self-healing agent.
"""

import sys
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config
from state_store import init_db, get_active_indexes, get_recent_decisions, get_benchmark_history
from pg_stats_reader import get_table_stats, get_index_stats, get_top_queries_by_time
from unused_index_detector import get_unused_indexes, get_index_usage_stats
from safety_guard import get_safety_report

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="VortexDBA",
    description="Autonomous Database Performance Optimizer",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DASHBOARD_HTML_PATH = Path(__file__).parent / "templates" / "dashboard.html"

# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard page."""
    if DASHBOARD_HTML_PATH.exists():
        with open(DASHBOARD_HTML_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>VortexDBA Dashboard HTML dosyası bulunamadı.</h1>", status_code=404)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/stats")
async def api_stats():
    """Get database statistics."""
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
        import traceback
        traceback.print_exc()
        return {
            "tables": [],
            "indexes": [],
            "top_queries": [],
            "error": str(e),
        }


@app.get("/api/indexes")
async def api_indexes():
    """Get active custom indexes in SQL Server with usage scans and redundancy analysis."""
    try:
        from db_connection import execute_query
        query = """
            SELECT 
                s.name AS schema_name,
                t.name AS table_name,
                i.name AS index_name,
                i.type_desc AS index_type,
                i.is_unique,
                STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns,
                COUNT(c.name) AS column_count,
                ISNULL(ius.user_seeks + ius.user_scans + ius.user_lookups, 0) AS total_scans
            FROM sys.indexes i
            JOIN sys.tables t ON t.object_id = i.object_id
            JOIN sys.schemas s ON s.schema_id = t.schema_id
            JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
            JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
            LEFT JOIN sys.dm_db_index_usage_stats ius ON ius.object_id = i.object_id AND ius.index_id = i.index_id AND ius.database_id = DB_ID()
            WHERE t.is_ms_shipped = 0 
              AND i.name IS NOT NULL 
              AND i.is_primary_key = 0
              AND ic.is_included_column = 0
            GROUP BY s.name, t.name, i.name, i.type_desc, i.is_unique, ius.user_seeks, ius.user_scans, ius.user_lookups
            ORDER BY t.name, i.name
        """
        rows = execute_query(query) or []
        
        raw_indexes = []
        for r in rows:
            cols = [c.strip() for c in r["columns"].split(",")] if r["columns"] else []
            raw_indexes.append({
                "name": r["index_name"],
                "table": r["table_name"],
                "columns": cols,
                "column_count": len(cols),
                "is_composite": len(cols) > 1,
                "scans": r["total_scans"],
                "index_type": r["index_type"],
                "is_unique": r["is_unique"],
            })

        analyzed = []
        for idx in raw_indexes:
            table = idx["table"]
            name = idx["name"]
            cols_set = set(idx["columns"])
            scans = idx["scans"]

            superseded_by = []
            for other in raw_indexes:
                if other["table"] == table and other["name"] != name:
                    other_cols_set = set(other["columns"])
                    if cols_set.issubset(other_cols_set) and len(other_cols_set) > len(cols_set):
                        superseded_by.append(other["name"])

            if scans > 0:
                status_label = f"✅ Aktif ({scans} Tarama)"
                status_class = "badge-success"
                reason = "SQL Server bu indeksi aktif olarak kullanıyor."
            elif superseded_by:
                status_label = "⚠️ Atıl / Ezilen İndeks"
                status_class = "badge-warning"
                reason = f"Bu kolon [{superseded_by[0]}] kompozit indeksi içinde yer aldığından SQL Server bunu kullanmıyor (0 Tarama)."
            else:
                status_label = "⏳ Trafik Bekliyor"
                status_class = "badge-info"
                reason = "İndeks oluşturuldu ancak henüz bu kolona ait sorgu çalıştırılmadı (0 Tarama)."

            analyzed.append({
                **idx,
                "status_label": status_label,
                "status_class": status_class,
                "reason": reason,
                "superseded_by": superseded_by,
            })

        return {"indexes": analyzed}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"indexes": [], "error": str(e)}


@app.get("/api/unused-indexes")
async def api_unused_indexes():
    """Get unused indexes with explanatory redundancy reasons."""
    try:
        from db_connection import execute_query
        from unused_index_detector import get_unused_indexes

        unused = get_unused_indexes()

        # Get all active indexes to find superseding composite indexes
        q = """
            SELECT t.name AS table_name, i.name AS index_name,
                   STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns
            FROM sys.indexes i
            JOIN sys.tables t ON t.object_id = i.object_id
            JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
            JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
            WHERE t.is_ms_shipped = 0 AND i.name IS NOT NULL AND i.is_primary_key = 0 AND ic.is_included_column = 0
            GROUP BY t.name, i.name
        """
        all_rows = execute_query(q) or []
        all_idx = {}
        for r in all_rows:
            all_idx[r["index_name"]] = {
                "table": r["table_name"],
                "columns": set([c.strip() for c in r["columns"].split(",")] if r["columns"] else [])
            }

        unused_list = []
        for idx in unused:
            cols_set = set(idx.columns)
            superseded_by = []
            for other_name, other_info in all_idx.items():
                if other_info["table"] == idx.table_name and other_name != idx.index_name:
                    if cols_set.issubset(other_info["columns"]) and len(other_info["columns"]) > len(cols_set):
                        superseded_by.append(other_name)

            if superseded_by:
                reason = f"[{superseded_by[0]}] kompozit indeksi bu kolonu da kapsadığı için SQL Server bu tekli indeksi hiç kullanmıyor."
                category = "Kompozit İndeks Tarafından Eziliyor"
            else:
                reason = "İndeks oluşturuldu ancak henüz bu kolona ait sorgu trafiği akmadı."
                category = "Henüz Trafik Görmedi"

            unused_list.append({
                "name": idx.index_name,
                "table": idx.table_name,
                "columns": idx.columns,
                "size": idx.index_size_pretty,
                "drop_statement": idx.drop_statement,
                "category": category,
                "reason": reason,
            })

        return {
            "unused_indexes": unused_list,
            "total_reclaimable": sum(idx.index_size_bytes for idx in unused),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"unused_indexes": [], "total_reclaimable": 0, "error": str(e)}


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
        import traceback
        traceback.print_exc()
        return {"decisions": [], "error": str(e)}


QUERY_CORE_METADATA = {
    "full_scan_status_filter": {
        "title": "Sipariş Durum & Tutar Filtresi",
        "table": "orders",
        "columns": ["status", "total_amount"],
        "description": "orders tablosunda WHERE status = 'completed' AND total_amount > 1000 filtresi",
        "baseline_ms": 1540.0,
    },
    "like_search": {
        "title": "E-posta LIKE Pattern Arama",
        "table": "customers",
        "columns": ["email"],
        "description": "customers tablosunda WHERE email LIKE '%@gmail.com' araması (Wildcard)",
        "baseline_ms": 185.0,
    },
    "subquery_aggregation": {
        "title": "Tekrarlanan Alt Sorgu (Subquery)",
        "table": "orders",
        "columns": ["customer_id", "total_amount"],
        "description": "orders üzerinde müşteri bazlı toplam harcama alt sorgusu",
        "baseline_ms": 145.0,
    },
    "group_by_having": {
        "title": "HAVING Filtreli GROUP BY",
        "table": "orders",
        "columns": ["customer_id", "total_amount"],
        "description": "orders tablosunda müşteri toplam harcamasına göre HAVING koşulu",
        "baseline_ms": 125.0,
    },
    "heavy_join": {
        "title": "Ağır Müşteri-Sipariş JOIN",
        "table": "customers",
        "columns": ["country", "customer_id"],
        "description": "customers ve orders arasında gruplamalı ve toplam tutarlı JOIN",
        "baseline_ms": 98.0,
    },
    "range_scan_large": {
        "title": "Tarih Aralığı Taraması (Range Scan)",
        "table": "orders",
        "columns": ["order_date"],
        "description": "orders tablosunda WHERE order_date BETWEEN ... aralık araması",
        "baseline_ms": 78.0,
    },
    "multi_condition_no_index": {
        "title": "Çoklu Kolon Filtresi (Multi-Condition)",
        "table": "customers",
        "columns": ["city", "country", "status"],
        "description": "customers tablosunda city, country, status çoklu AND araması",
        "baseline_ms": 32.0,
    },
    "full_scan_no_index": {
        "title": "Müşteri Şehir Filtresi",
        "table": "customers",
        "columns": ["city"],
        "description": "customers tablosunda WHERE city = '...' araması",
        "baseline_ms": 11.5,
    },
}


@app.get("/api/performance-matrix")
async def api_performance_matrix():
    """Get before/after performance comparison matrix dynamically matched to SQL Server."""
    try:
        from db_connection import execute_query
        from slow_queries import SLOW_QUERIES
        from state_store import get_benchmark_history

        # Query all live indexes and their column lists from SQL Server
        q_idx = """
            SELECT 
                t.name AS table_name,
                i.name AS index_name,
                STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns
            FROM sys.indexes i
            JOIN sys.tables t ON t.object_id = i.object_id
            JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
            JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
            WHERE t.is_ms_shipped = 0 AND i.name IS NOT NULL AND i.is_primary_key = 0 AND ic.is_included_column = 0
            GROUP BY t.name, i.name
        """
        active_rows = execute_query(q_idx) or []

        matrix = []
        for q in SLOW_QUERIES:
            name = q["name"]
            meta = QUERY_CORE_METADATA.get(name, {
                "title": name,
                "table": "N/A",
                "columns": [],
                "description": q.get("description", ""),
                "baseline_ms": 100.0,
            })

            target_table = meta["table"]
            target_cols = set(meta["columns"])
            baseline_ms = meta["baseline_ms"]

            # Dynamically find which active SQL Server indexes cover these query columns
            matching_active_indexes = []
            for row in active_rows:
                tbl = row["table_name"]
                idx_name = row["index_name"]
                idx_cols = set([c.strip() for c in row["columns"].split(",")] if row["columns"] else [])

                # Match if same table and shares filter columns
                if (tbl in target_table or target_table in tbl) and (target_cols.intersection(idx_cols)):
                    matching_active_indexes.append(idx_name)

            has_index = len(matching_active_indexes) > 0
            hist = get_benchmark_history(name, 5)

            if not has_index:
                current_ms = None
                speedup_pct = None
                multiplier = None
                status_label = "🐢 İndeks Bekliyor"
                status_class = "badge-danger"
            elif not hist:
                # Index exists in SQL Server, but benchmark hasn't been run yet
                current_ms = None
                speedup_pct = None
                multiplier = None
                status_label = "⏳ Test Bekliyor"
                status_class = "badge-warning"
            else:
                # Real benchmark history is available
                current_ms = hist[0].mean_ms

                if baseline_ms > current_ms and current_ms > 0:
                    speedup_pct = round(((baseline_ms - current_ms) / baseline_ms) * 100, 1)
                    multiplier = round(baseline_ms / current_ms, 1)
                else:
                    speedup_pct = 0.0
                    multiplier = 1.0

                if current_ms < 15:
                    status_label = "🚀 Süper Hızlı"
                    status_class = "badge-success"
                elif current_ms < 50:
                    status_label = "⚡ Hızlı"
                    status_class = "badge-info"
                else:
                    status_label = "Orta"
                    status_class = "badge-warning"

            matrix.append({
                "name": name,
                "title": meta["title"],
                "table": meta["table"],
                "columns": ", ".join(meta["columns"]),
                "active_indexes": matching_active_indexes,
                "has_index": has_index,
                "description": meta["description"],
                "query_sql": q["query"].strip(),
                "baseline_ms": round(baseline_ms, 2),
                "current_ms": round(current_ms, 2) if current_ms is not None else None,
                "speedup_pct": speedup_pct,
                "multiplier": multiplier,
                "status_label": status_label,
                "status_class": status_class,
            })

        matrix.sort(key=lambda x: x["baseline_ms"], reverse=True)
        return {"matrix": matrix, "active_index_count": len(active_rows)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"matrix": [], "error": str(e)}


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
        import traceback
        traceback.print_exc()
        return {"query_name": query_name, "history": [], "error": str(e)}


@app.get("/api/safety-report")
async def api_safety_report():
    """Get safety status report."""
    try:
        report = get_safety_report()
        return {"report": report}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"report": str(e), "error": str(e)}


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


@app.get("/api/recommendations")
async def api_recommendations():
    """Get actionable index recommendations from query analysis."""
    try:
        from auto_remediator import run_full_analysis
        recs = run_full_analysis()
        return {
            "recommendations": [
                {
                    "table": r.table,
                    "columns": r.columns,
                    "reason": r.reason,
                    "priority": r.priority,
                    "create_sql": r.create_statement,
                    "index_name": r.index_name,
                }
                for r in recs
            ]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"recommendations": [], "error": str(e)}



@app.post("/api/actions/remediate")
async def api_action_remediate(payload: dict | None = None):
    """Run remediation (apply or dry-run)."""
    try:
        dry_run = (payload or {}).get("dry_run", True)
        from auto_remediator import run_remediation
        report = run_remediation(dry_run=dry_run, apply=not dry_run, compare=True, rollback=True)
        return {
            "success": True,
            "dry_run": report.dry_run,
            "applied_count": len([x for x in report.applied_indexes if x.applied]),
            "applied_indexes": [
                {
                    "name": x.index_name,
                    "table": x.table,
                    "duration_ms": x.duration_ms,
                    "applied": x.applied,
                    "error": x.error,
                }
                for x in report.applied_indexes
            ],
            "rolled_back": report.rolled_back,
            "errors": report.errors,
            "comparisons": [
                {
                    "name": c.name,
                    "before_mean_ms": round(c.before_mean_ms, 2),
                    "after_mean_ms": round(c.after_mean_ms, 2),
                    "improvement_pct": round(c.improvement_pct, 1),
                    "verdict": c.verdict,
                }
                for c in report.comparisons
            ],
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/stream/simulate-load")
async def api_stream_simulate_load():
    """Stream slow query workload simulation line by line."""
    def gen():
        from datetime import datetime
        import time
        from slow_queries import SLOW_QUERIES, run_query

        t0 = datetime.now().strftime("%H:%M:%S")
        yield f"[{t0}] ⚡ SQL Server Yavaş Sorgu Trafiği Başlatılıyor...\n"
        yield f"[{t0}] Toplam {len(SLOW_QUERIES)} sorgu senaryosu çalıştırılacak.\n"
        yield "=" * 65 + "\n"

        total_ms = 0
        for i, q in enumerate(SLOW_QUERIES, 1):
            t_now = datetime.now().strftime("%H:%M:%S")
            yield f"[{t_now}] [{i}/{len(SLOW_QUERIES)}] Koşturuluyor: {q['name']} ... "
            res = run_query(q)
            total_ms += res.duration_ms
            status_color = "[KRİTİK YAVAŞ]" if res.duration_ms > 500 else ("[YAVAŞ]" if res.duration_ms > 50 else "[HIZLI]")
            yield f"{res.duration_ms:.2f} ms | {res.row_count:,} satır {status_color}\n"
            time.sleep(0.03)

        t_end = datetime.now().strftime("%H:%M:%S")
        yield "=" * 65 + "\n"
        yield f"[{t_end}] ✔ Tamamlandı! Toplam süre: {total_ms:.2f} ms. SQL Server DMV sayaçları güncellendi.\n"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")


@app.post("/api/stream/remediate")
async def api_stream_remediate(payload: dict = {}):
    """Stream auto-remediation logs line by line."""
    dry_run = payload.get("dry_run", False)

    def gen():
        from datetime import datetime
        from auto_remediator import (
            get_slow_queries_for_benchmark, run_full_analysis,
            apply_index, drop_index, _extract_index_name
        )
        from benchmark import run_benchmark_suite, compare_results
        from safety_guard import check_safety, SafetyViolation
        from state_store import (
            record_decision, record_index_applied, record_index_rolled_back, record_benchmark
        )

        t0 = datetime.now().strftime("%H:%M:%S")
        yield f"[{t0}] 🚀 VortexDBA Otomatik İyileştirme Başlatıldı (dry_run={dry_run})...\n"
        yield "=" * 65 + "\n"

        # Step 1: Analyze
        t1 = datetime.now().strftime("%H:%M:%S")
        yield f"[{t1}] [1/5] 🔍 SQL Server sorguları analiz ediliyor & indeks tavsiyeleri üretiliyor...\n"
        recs = run_full_analysis()
        if not recs:
            yield "  -> Herhangi bir indeks eksikliği veya darboğaz tespit edilmedi.\n"
        else:
            for r in recs:
                yield f"  💡 Tavsiye: {r.table} tablosuna ({', '.join(r.columns)}) için indeks -> {r.reason}\n"
                yield f"     SQL: {r.create_statement}\n"

        # Step 2: Before Benchmarks
        t2 = datetime.now().strftime("%H:%M:%S")
        yield f"\n[{t2}] [2/5] ⏱️ İyileştirme ÖNCESİ benchmark çalıştırılıyor (3 tur)... \n"
        queries = get_slow_queries_for_benchmark()
        before_res = run_benchmark_suite(queries, runs=3)
        for b in before_res:
            yield f"  - {b.name:<30}: {b.mean_ms:>8.2f} ms\n"

        # Step 3: Apply Indexes
        applied_results = []
        if not dry_run and recs:
            t3 = datetime.now().strftime("%H:%M:%S")
            yield f"\n[{t3}] [3/5] 🛠️ İndeksler SQL Server veritabanına uygulanıyor...\n"
            for rec in recs:
                idx_name = _extract_index_name(rec.create_statement)
                try:
                    check_safety(rec.table, idx_name, ignore_cooldown=True)
                    yield f"  -> Uygulanıyor: {idx_name} on {rec.table}... "
                    res = apply_index(rec)
                    applied_results.append(res)
                    if res.applied:
                        record_index_applied(res.index_name, res.table, res.columns, res.create_sql, rec.reason)
                        record_decision("applied", f"Uygulandı: [{res.index_name}] on [{res.table}]")
                        yield f"[OK] ({res.duration_ms:.0f} ms)\n"
                    else:
                        yield f"[HATA] {res.error}\n"
                except SafetyViolation as sv:
                    record_decision("safety_skip", f"{idx_name}: {sv}")
                    yield f"[GÜVENLİK ATLAMASI] {sv}\n"
        elif dry_run:
            yield "\n[3/5] 🧪 Simülasyon modu aktif; indeksler veritabanına uygulanmadı.\n"

        # Step 4: After Benchmarks
        after_res = []
        comparisons = []
        if not dry_run and applied_results:
            t4 = datetime.now().strftime("%H:%M:%S")
            yield f"\n[{t4}] [4/5] ⏱️ İyileştirme SONRASI benchmark çalıştırılıyor (3 tur)... \n"
            after_res = run_benchmark_suite(queries, runs=3)
            for b in after_res:
                record_benchmark(b.name, b.mean_ms, b.median_ms)

            comparisons = compare_results(before_res, after_res, threshold_pct=10.0)
            for c in comparisons:
                trend = f"▲ %{c.improvement_pct:.1f} HIZLANDI" if c.improvement_pct > 0 else (f"▼ %{abs(c.improvement_pct):.1f} YAVAŞLADI" if c.verdict == "degraded" else "DEĞİŞMEDİ")
                yield f"  - {c.name:<30}: {c.before_mean_ms:>7.2f} ms -> {c.after_mean_ms:>7.2f} ms  [{trend}]\n"

        # Step 5: Rollback Check
        if not dry_run and comparisons:
            t5 = datetime.now().strftime("%H:%M:%S")
            yield f"\n[{t5}] [5/5] 🛡️ Yavaşlama (Degradation) kontrolü yapılıyor...\n"
            degraded = [c for c in comparisons if c.verdict == "degraded"]
            if degraded:
                yield f"  ⚠️ {len(degraded)} sorguda yavaşlama tespit edildi! Güvenlik gereği geri alınıyor:\n"
                for r in applied_results:
                    if r.applied:
                        drop_index(r.index_name, r.table)
                        record_index_rolled_back(r.index_name)
                        record_decision("rollback", f"Geri alındı: [{r.index_name}]")
                        yield f"    - Silindi (Rollback): {r.index_name}\n"
            else:
                yield f"  ✔ Hiçbir yavaşlama tespit edilmedi! Tüm uygulanan indeksler korundu.\n"

        t_fin = datetime.now().strftime("%H:%M:%S")
        yield "=" * 65 + "\n"
        yield f"[{t_fin}] ✔ İŞLEM BAŞARIYLA TAMAMLANDI.\n"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")


@app.post("/api/stream/run-benchmark")
async def api_stream_run_benchmark():
    """Stream live benchmark testing logs line by line."""
    def gen():
        from datetime import datetime
        from auto_remediator import get_slow_queries_for_benchmark
        from benchmark import run_benchmark
        from state_store import get_benchmark_history, record_benchmark

        t0 = datetime.now().strftime("%H:%M:%S")
        yield f"[{t0}] 📊 Canlı Hız & Performans Testi Başlatıldı (Her sorgu 3 tur test ediliyor)...\n"
        yield "=" * 65 + "\n"

        queries = get_slow_queries_for_benchmark()
        for i, q in enumerate(queries, 1):
            t_now = datetime.now().strftime("%H:%M:%S")
            yield f"[{t_now}] [{i}/{len(queries)}] Test ediliyor: {q['name']} ... "
            res = run_benchmark(q["name"], q["query"], q.get("params"), runs=3)

            history = get_benchmark_history(res.name, 2)
            prev_ms = history[0].mean_ms if history else None
            record_benchmark(res.name, res.mean_ms, res.median_ms)

            trend_str = ""
            if prev_ms:
                diff_pct = ((prev_ms - res.mean_ms) / prev_ms) * 100
                if diff_pct > 0:
                    trend_str = f"(Önceki: {prev_ms:.1f}ms | ▲ %{diff_pct:.1f} Hızlandı)"
                elif diff_pct < 0:
                    trend_str = f"(Önceki: {prev_ms:.1f}ms | ▼ %{abs(diff_pct):.1f} Yavaşladı)"

            cat = "SÜPER HIZLI" if res.mean_ms < 10 else ("HIZLI" if res.mean_ms < 50 else "YAVAŞ")
            yield f"Ort: {res.mean_ms:.2f} ms (min: {res.min_ms:.1f}ms, max: {res.max_ms:.1f}ms) [{cat}] {trend_str}\n"

        t_end = datetime.now().strftime("%H:%M:%S")
        yield "=" * 65 + "\n"
        yield f"[{t_end}] ✔ Canlı benchmark tamamlandı. 8 sorgu başarıyla ölçüldü.\n"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")


@app.post("/api/stream/reset-indexes")
async def api_stream_reset_indexes():
    """Stream reset-indexes logs line by line."""
    def gen():
        from datetime import datetime
        from db_connection import get_connection, execute_query
        import sqlite3
        from state_store import DB_PATH, record_decision

        t0 = datetime.now().strftime("%H:%M:%S")
        yield f"[{t0}] 🧹 Tüm Özel İndeksleri Sıfırlama İşlemi Başlatıldı...\n"
        yield "=" * 65 + "\n"

        query = """
            SELECT s.name AS schema_name, t.name AS table_name, i.name AS index_name
            FROM sys.indexes i
            JOIN sys.tables t ON t.object_id = i.object_id
            JOIN sys.schemas s ON s.schema_id = t.schema_id
            WHERE t.is_ms_shipped = 0 AND i.name IS NOT NULL
              AND i.is_primary_key = 0 AND i.is_unique_constraint = 0
        """
        indexes = execute_query(query) or []
        yield f"[{t0}] SQL Server üzerinde {len(indexes)} adet özel indeks tespit edildi.\n"

        conn = get_connection(autocommit=True)
        with conn.cursor() as cur:
            for idx in indexes:
                t = idx['table_name']
                name = idx['index_name']
                yield f"  🗑️ Siliniyor: [{name}] on [{t}] ... "
                cur.execute(f"DROP INDEX IF EXISTS [{name}] ON [{t}]")
                yield "[OK]\n"
            try:
                yield f"[{t0}] SQL Server sorgu önbelleği temizleniyor (DBCC FREEPROCCACHE) ... "
                cur.execute("DBCC FREEPROCCACHE")
                yield "[OK]\n"
            except Exception as e:
                yield f"[NOT: {e}]\n"
        conn.close()

        if DB_PATH.exists():
            sconn = sqlite3.connect(str(DB_PATH))
            sconn.execute("DELETE FROM applied_indexes")
            sconn.execute("DELETE FROM agent_decisions")
            sconn.execute("DELETE FROM benchmark_history")
            sconn.commit()
            sconn.close()
            yield f"[{t0}] SQLite karar, indeks ve benchmark geçmişi sıfırlandı ... [OK]\n"

        record_decision("reset_all", f"Tüm özel indeksler ({len(indexes)} adet) sıfırlandı.")
        t_end = datetime.now().strftime("%H:%M:%S")
        yield "=" * 65 + "\n"
        yield f"[{t_end}] ✔ SIFIRLAMA TAMAMLANDI. Sistem tertemiz başlangıç durumunda!\n"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")


@app.post("/api/stream/drop-index")
async def api_stream_drop_index(payload: dict):
    """Stream dropping a single index."""
    index_name = payload.get("index_name")
    table_name = payload.get("table_name")

    def gen():
        from datetime import datetime
        from auto_remediator import drop_index
        from state_store import record_decision

        t0 = datetime.now().strftime("%H:%M:%S")
        yield f"[{t0}] 🗑️ İndeks Silme: [{index_name}] on [{table_name}]...\n"
        success = drop_index(index_name, table_name)
        if success:
            record_decision("manual_drop", f"Silindi: [{index_name}] ({table_name})")
            yield f"[{t0}] ✔ [{index_name}] indeksi başarıyla SQL Server'dan kaldırıldı.\n"
        else:
            yield f"[{t0}] ❌ [{index_name}] silinemedi!\n"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")





if __name__ == "__main__":
    import uvicorn
    print("VortexDBA Dashboard baslatiliyor: http://localhost:8050")
    uvicorn.run("web_app:app", host="127.0.0.1", port=8050, reload=True)

