"""Asynchronous background QThread workers for VortexDBA native GUI."""

import time
import traceback
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal

try:
    from src.slow_queries import SLOW_QUERIES
    from src.db_connection import (
        execute_query,
        test_connection,
        check_current_connection,
        apply_schema_script,
    )
    from src.auto_remediator import run_remediation
    from src.benchmark import run_benchmark_suite, compare_results
    from src.state_store import (
        record_baseline,
        get_latest_baseline,
        get_active_indexes,
        record_index_rolled_back,
        record_benchmark,
    )
except ImportError:
    from slow_queries import SLOW_QUERIES
    from db_connection import (
        execute_query,
        test_connection,
        check_current_connection,
        apply_schema_script,
    )
    from auto_remediator import run_remediation
    from benchmark import run_benchmark_suite, compare_results
    from state_store import (
        record_baseline,
        get_latest_baseline,
        get_active_indexes,
        record_index_rolled_back,
        record_benchmark,
    )


class SimulateWorker(QThread):
    """Runs 15 slow queries and emits real-time log lines."""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def run(self):
        start_time = datetime.now()
        self.log_signal.emit(f"🚀 [TRAFİK SİMÜLASYONU BAŞLATILDI] {start_time.strftime('%H:%M:%S')}\n"
                             f"📋 Toplam 15 adet darboğaz T-SQL sorgusu SQL Server üzerinde çalıştırılıyor...\n"
                             f"{'=' * 65}\n")
        
        # Connection pre-check
        health = check_current_connection(timeout=2)
        if not health.get("success"):
            err_msg = (f"❌ [BAĞLANTI HATASI]: SQL Server'a ulaşılamıyor ({health.get('host')}:{health.get('port')}).\n"
                       f"   Hata: {health.get('error')}\n"
                       f"   💡 Lütfen SQL Server'ı başlatın veya üstteki 'Sunucuya Bağlan' panelinden ayarları kontrol edin.\n")
            self.log_signal.emit(err_msg)
            self.finished_signal.emit(False, err_msg)
            return

        success_count = 0
        total_time = 0.0
        active_indexes = get_active_indexes()
        has_custom_indexes = len(active_indexes) > 0

        for i, q in enumerate(SLOW_QUERIES, 1):
            name = q["name"]
            title = q.get("title", name)
            sql = q["query"]

            self.log_signal.emit(f"[{i:02d}/15] {title}...\n    SQL: {sql[:75]}...")
            
            try:
                t0 = time.time()
                rows = execute_query(sql, params=q.get("params")) or []
                duration_ms = (time.time() - t0) * 1000


                success_count += 1
                total_time += duration_ms

                record_baseline(name, duration_ms)
                self.log_signal.emit(f"    ⏱ Süre: {duration_ms:.1f} ms | Satır: {len(rows):,} | 📌 Baseline Kaydedildi\n")

            except Exception as e:
                self.log_signal.emit(f"    ❌ HATA: {e}\n")

            time.sleep(0.05)

        avg_time = total_time / max(success_count, 1)
        summary = (f"{'=' * 65}\n"
                   f"✔ [SİMÜLASYON TAMAMLANDI]\n"
                   f"   Başarılı Sorgular: {success_count}/{len(SLOW_QUERIES)}\n"
                   f"   Toplam Süre: {total_time:.1f} ms | Ortalama Süre: {avg_time:.1f} ms\n")
        self.log_signal.emit(summary)
        self.finished_signal.emit(True, summary)


class RemediateWorker(QThread):
    """Runs auto-remediation with IndexAdvisor and ONLINE=ON."""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, dry_run: bool = False):
        super().__init__()
        self.dry_run = dry_run

    def run(self):
        start_time = datetime.now()
        self.log_signal.emit(f"⚡ [OTOMATİK İNDEKSLENME BAŞLATILDI] {start_time.strftime('%H:%M:%S')}\n"
                             f"🔍 Dynamic AST IndexAdvisor kuralları çalıştırılıyor...\n"
                             f"{'=' * 65}\n")
        
        # Connection pre-check
        health = check_current_connection(timeout=2)
        if not health.get("success"):
            err_msg = (f"❌ [BAĞLANTI HATASI]: SQL Server'a ulaşılamıyor ({health.get('host')}:{health.get('port')}).\n"
                       f"   Hata: {health.get('error')}\n"
                       f"   💡 Lütfen SQL Server bağlantısını sağlayıp tekrar deneyin.\n")
            self.log_signal.emit(err_msg)
            self.finished_signal.emit(False, err_msg)
            return

        try:
            from src.state_store import get_captured_queries
            from src.index_advisor import recommend_index_for_query
            from src.pg_stats_reader import get_top_queries_by_time

            applied_count = 0
            applied_names = set()

            captured = get_captured_queries()
            if captured:
                queries_to_index = [q["query_sql"] for q in captured]
            else:
                stats = get_top_queries_by_time(limit=15)
                queries_to_index = [s.query for s in stats if s.query]

            recs = []
            for sql in queries_to_index:
                rec = recommend_index_for_query(sql)
                if rec and rec.index_name not in applied_names:
                    recs.append(rec)
                    applied_names.add(rec.index_name)

            if not recs:
                msg = "ℹ [BİLGİ] Önerilen yeni bir indeks bulunamadı veya tüm sorgular zaten indeksli.\n"
                self.log_signal.emit(msg)
                self.finished_signal.emit(True, msg)
                return

            for rec in recs:
                self.log_signal.emit(f"⚙ [OLUŞTURULUYOR] {rec.index_name} -> {rec.table}\n"
                                     f"   DDL: {rec.create_statement}")
                t0 = time.time()
                try:
                    execute_query(rec.create_statement, autocommit=True)
                    elapsed_ms = (time.time() - t0) * 1000
                    record_index_applied(rec.index_name, rec.table, rec.columns, rec.create_statement, rec.reason)
                    applied_count += 1
                    self.log_signal.emit(f"   ✔ [OLUŞTURULDU] ({elapsed_ms:.0f} ms)\n")
                except Exception as e:
                    self.log_signal.emit(f"   ❌ [HATA]: {e}\n")

            summary = (f"{'=' * 65}\n"
                       f"✔ [İNDEKSLER OLUŞTURULDU] Toplam {applied_count} özel indeks başarıyla oluşturuldu.\n")
            self.log_signal.emit(summary)
            self.finished_signal.emit(True, summary)
        except Exception as e:
            err_msg = f"❌ [KRİTİK HATA]: {traceback.format_exc()}\n"
            self.log_signal.emit(err_msg)
            self.finished_signal.emit(False, err_msg)



class BenchmarkWorker(QThread):
    """Runs live 3-iteration benchmark comparison for currently active queries."""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, queries: list[dict] | None = None):
        super().__init__()
        self.queries = queries

    def run(self):
        start_time = datetime.now()
        self.log_signal.emit(f"📊 [CANLI BENCHMARK BAŞLATILDI] {start_time.strftime('%H:%M:%S')}\n"
                             f"🔬 3-İterasyonlu İndeks Öncesi vs İndeks Sonrası Kıyaslama Testi...\n"
                             f"{'=' * 65}\n")
        
        # Connection pre-check
        health = check_current_connection(timeout=2)
        if not health.get("success"):
            err_msg = (f"❌ [BAĞLANTI HATASI]: SQL Server'a ulaşılamıyor ({health.get('host')}:{health.get('port')}).\n"
                       f"   Hata: {health.get('error')}\n"
                       f"   💡 Lütfen SQL Server bağlantısını sağlayıp tekrar deneyin.\n")
            self.log_signal.emit(err_msg)
            self.finished_signal.emit(False, err_msg)
            return

        try:
            if self.queries:
                queries = self.queries
            else:
                from src.state_store import get_captured_queries
                captured = get_captured_queries()
                if captured:
                    queries = [{"name": q["query_name"], "query": q["query_sql"], "params": None} for q in captured]
                else:
                    from src.pg_stats_reader import get_top_queries_by_time
                    stats = get_top_queries_by_time(limit=15)
                    queries = [{"name": f"live_{s.queryid}", "query": s.query, "params": None} for s in stats if s.query]

            if not queries:
                msg = "ℹ [BİLGİ] Benchmark edilecek sorgu bulunamadı (Tabloda aktif sorgu yok).\n"
                self.log_signal.emit(msg)
                self.finished_signal.emit(True, msg)
                return


            self.log_signal.emit(f"📋 Tablodaki {len(queries)} adet aktif sorgu test ediliyor...\n")
            results = run_benchmark_suite(queries, runs=3)


            total_base = 0.0
            total_curr = 0.0
            speedups = []

            for r in results:
                name = r.name
                curr_ms = r.mean_ms
                record_benchmark(name, curr_ms, r.median_ms)

                base_ms = get_latest_baseline(name) or curr_ms
                total_base += base_ms
                total_curr += curr_ms

                if base_ms > 0 and curr_ms > 0:
                    pct = round(((base_ms - curr_ms) / base_ms) * 100, 1)
                    mult = round(base_ms / curr_ms, 1)
                    if mult > 1:
                        speedups.append(mult)
                    speed_str = f"▲ {mult:.1f}x Hızlı (%{pct:.1f})" if pct > 0 else f"%{pct:.1f}"
                else:
                    speed_str = "—"

                self.log_signal.emit(f"• {name}:\n"
                                     f"    İndekssiz: {base_ms:.1f} ms -> İndeksli: {curr_ms:.1f} ms | {speed_str}\n")

            avg_base = total_base / max(len(results), 1)
            avg_curr = total_curr / max(len(results), 1)
            overall_speedup = ((avg_base - avg_curr) / avg_base) * 100 if avg_base > 0 else 0
            overall_mult = avg_base / avg_curr if avg_curr > 0 else 1.0

            summary = (f"{'=' * 65}\n"
                       f"✔ [BENCHMARK TAMAMLANDI]\n"
                       f"   Ortalama İndekssiz (Baseline): {avg_base:.1f} ms\n"
                       f"   Ortalama İndeksli (Current): {avg_curr:.1f} ms\n"
                       f"   Ortalama Hızlanma Kazancı: %{overall_speedup:.1f} ({overall_mult:.1f}x Hızlı)\n")
            self.log_signal.emit(summary)
            self.finished_signal.emit(True, summary)
        except Exception as e:
            err_msg = f"❌ [BENCHMARK HATASI]: {traceback.format_exc()}\n"
            self.log_signal.emit(err_msg)
            self.finished_signal.emit(False, err_msg)


class ResetWorker(QThread):
    """Drops custom indexes or performs full factory reset."""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, full_reset: bool = False):
        super().__init__()
        self.full_reset = full_reset

    def run(self):
        if self.full_reset:
            self.log_signal.emit(f"💥 [FABRİKA SIFIRLAMASI BAŞLATILDI]\n"
                                 f"🗑 Tüm özel indeksler kaldırılıyor ve baseline ölçümleri temizleniyor...\n")
        else:
            self.log_signal.emit(f"↺ [İNDEKSLER SIFIRLANIYOR]\n"
                                 f"🗑 SQL Server üzerindeki özel optimizasyon indeksleri kaldırılıyor...\n")

        try:
            # Query SQL Server directly for all custom non-PK/non-unique indexes
            DEFAULT_INDEXES = {"idx_orders_customer_id", "idx_customers_email"}
            q_find = """
                SELECT t.name AS table_name, i.name AS index_name
                FROM sys.indexes i
                JOIN sys.tables t ON t.object_id = i.object_id
                WHERE t.is_ms_shipped = 0 AND i.name IS NOT NULL
                  AND i.is_primary_key = 0 AND i.is_unique_constraint = 0
            """
            live_indexes = execute_query(q_find) or []
            custom_to_drop = [r for r in live_indexes if r["index_name"] not in DEFAULT_INDEXES]

            drop_count = 0
            for r in custom_to_drop:
                index_name = r["index_name"]
                table_name = r["table_name"]
                drop_sql = f"IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = '{index_name}') DROP INDEX [{index_name}] ON [{table_name}];"
                try:
                    execute_query(drop_sql, autocommit=True)
                    record_index_rolled_back(index_name)
                    drop_count += 1
                    self.log_signal.emit(f"   ✔ Kaldırıldı: [{index_name}] on [{table_name}]\n")
                except Exception as e:
                    self.log_signal.emit(f"   ❌ Kaldırılamadı [{index_name}]: {e}\n")

            # Always clear plan cache and drop clean buffers for accurate cold timing
            try:
                execute_query("DBCC FREEPROCCACHE;", autocommit=True)
                execute_query("DBCC DROPCLEANBUFFERS;", autocommit=True)
                self.log_signal.emit("   ✔ SQL Server Plan Önbelleği ve Buffer Pool (RAM) temizlendi.\n")
            except Exception:
                pass

            if self.full_reset:
                try:
                    from src.state_store import clear_all_state
                    clear_all_state()
                except Exception:
                    pass
                self.log_signal.emit("   ✔ Durum deposu ve tüm baseline süreleri sıfırlandı.\n")

            summary = f"✔ [SIFIRLAMA TAMAMLANDI] Toplam {drop_count} özel indeks SQL Server'dan tamamen silindi.\n"
            self.log_signal.emit(summary)
            self.finished_signal.emit(True, summary)
        except Exception as e:
            err_msg = f"❌ [SIFIRLAMA HATASI]: {e}\n"
            self.log_signal.emit(err_msg)
            self.finished_signal.emit(False, err_msg)



class DbPingWorker(QThread):
    """Non-blocking background test ping for database connection."""
    result_signal = pyqtSignal(dict)

    def __init__(self, host, port, dbname, user, password, timeout=3):
        super().__init__()
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = password
        self.timeout = timeout

    def run(self):
        start = time.time()
        res = test_connection(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            timeout=self.timeout
        )
        latency_ms = int((time.time() - start) * 1000)
        res["latency_ms"] = latency_ms
        self.result_signal.emit(res)


class DbQuickCheckWorker(QThread):
    """Non-blocking background check of currently active database configuration."""
    result_signal = pyqtSignal(dict)

    def __init__(self, timeout=2):
        super().__init__()
        self.timeout = timeout

    def run(self):
        start = time.time()
        res = check_current_connection(timeout=self.timeout)
        latency_ms = int((time.time() - start) * 1000)
        res["latency_ms"] = latency_ms
        self.result_signal.emit(res)


class SchemaInitWorker(QThread):
    """Background worker to apply 01_schema.sql to target database."""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def run(self):
        self.log_signal.emit("📋 [ŞEMA KURULUMU BAŞLATILDI] 01_schema.sql hedef veritabanına uygulanıyor...\n")
        success, msg = apply_schema_script()
        if success:
            self.log_signal.emit(f"✔ [BAŞARILI] {msg}\n")
            self.finished_signal.emit(True, msg)
        else:
            self.log_signal.emit(f"❌ [HATA] {msg}\n")
            self.finished_signal.emit(False, msg)

