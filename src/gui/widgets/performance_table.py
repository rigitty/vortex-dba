"""Performance Matrix Table Widget for PyQt6."""

from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QWidget,
    QApplication,
    QSizePolicy,
)

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

try:
    from src.slow_queries import SLOW_QUERIES
    from src.state_store import get_active_indexes, get_benchmark_history, get_latest_baseline
    from src.index_advisor import recommend_index_for_query
    from src.config import get_config
    from src.db_connection import execute_query
    from src.pg_stats_reader import get_live_workload_matrix
except ImportError:
    from slow_queries import SLOW_QUERIES
    from state_store import get_active_indexes, get_benchmark_history, get_latest_baseline
    from index_advisor import recommend_index_for_query
    from config import get_config
    from db_connection import execute_query
    from pg_stats_reader import get_live_workload_matrix


class PerformanceMatrixWidget(QFrame):
    """Interactive Performance Matrix Table with search and status filtering."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card-panel")
        self.raw_data = []
        self.filter_mode = "all"

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header bar: Title, Search, and Filter Buttons
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(1)
        title_lbl = QLabel("Sorgu Performans & İndeks Optimizasyon Matrisi")
        title_lbl.setStyleSheet("font-size: 12.5px; font-weight: 700; color: #f1f5f9;")
        self.sub_lbl = QLabel("İndeks öncesi baseline ve indeks sonrası hızlanma kıyaslaması:")
        self.sub_lbl.setStyleSheet("font-size: 10px; color: #728499;")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(self.sub_lbl)
        header_row.addLayout(title_vbox)
        header_row.addStretch()

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tablo, kolon veya SQL ara...")
        self.search_input.setFixedWidth(180)
        self.search_input.setFixedHeight(26)
        self.search_input.textChanged.connect(self.filter_table)
        header_row.addWidget(self.search_input)

        # Filter buttons
        filter_box = QHBoxLayout()
        filter_box.setSpacing(3)
        self.btn_all = QPushButton("Tümü")
        self.btn_all.setProperty("class", "segment-btn")
        self.btn_all.setCheckable(True)
        self.btn_all.setChecked(True)
        self.btn_all.clicked.connect(lambda: self.set_filter("all"))
        filter_box.addWidget(self.btn_all)

        self.btn_slow = QPushButton("İndekssiz")
        self.btn_slow.setProperty("class", "segment-btn")
        self.btn_slow.setCheckable(True)
        self.btn_slow.clicked.connect(lambda: self.set_filter("slow"))
        filter_box.addWidget(self.btn_slow)

        self.btn_indexed = QPushButton("İndeksli")
        self.btn_indexed.setProperty("class", "segment-btn")
        self.btn_indexed.setCheckable(True)
        self.btn_indexed.clicked.connect(lambda: self.set_filter("indexed"))
        filter_box.addWidget(self.btn_indexed)

        self.btn_speedup = QPushButton("Hızlanan")
        self.btn_speedup.setProperty("class", "segment-btn")
        self.btn_speedup.setCheckable(True)
        self.btn_speedup.clicked.connect(lambda: self.set_filter("speedup"))
        filter_box.addWidget(self.btn_speedup)

        header_row.addLayout(filter_box)
        layout.addLayout(header_row)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Sorgu / T-SQL",
            "Tablo & Kolon",
            "İndekssiz",
            "İndeks Durumu / DDL",
            "İndeksli & Kazanç"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.verticalHeader().setVisible(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.table)


    def set_filter(self, mode: str):
        self.filter_mode = mode
        self.btn_all.setChecked(mode == "all")
        self.btn_slow.setChecked(mode == "slow")
        self.btn_indexed.setChecked(mode == "indexed")
        self.btn_speedup.setChecked(mode == "speedup")
        self.filter_table()


    def load_data(self, is_connected: bool = False):
        cfg = get_config()
        source = getattr(cfg, "traffic_source", "simulation")

        if source == "live_dmv":
            if is_connected:
                self.sub_lbl.setText("🔴 Canlı SQL Server DMV (sys.dm_exec_query_stats) Trafiği:")
                try:
                    self.raw_data = get_live_workload_matrix() or []
                except Exception as e:
                    self.sub_lbl.setText(f"⚠️ DMV Trafiği Alınamadı: {e}")
                    self.raw_data = []
            else:
                self.sub_lbl.setText("🔴 Canlı SQL Server DMV Trafiği (Çevrimdışı Mod - Sunucu Bağlantısı Bekleniyor)")
                self.raw_data = []
        else:
            self.sub_lbl.setText("🧪 15 Sentetik Test Sorgusu (İndeks Öncesi vs İndeks Sonrası):")
            try:
                vortex_applied = get_active_indexes()
            except Exception:
                vortex_applied = []
            vortex_applied_names = {idx.index_name for idx in vortex_applied}

            DEFAULT_SCHEMA_INDEXES = {"idx_orders_customer_id", "idx_customers_email"}
            all_active_rows = []

            if is_connected:
                q_idx = """
                    SELECT 
                        t.name AS table_name,
                        i.name AS index_name,
                        STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns
                    FROM sys.indexes i
                    JOIN sys.tables t ON t.object_id = i.object_id
                    JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
                    JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
                    WHERE t.is_ms_shipped = 0 AND i.name IS NOT NULL 
                      AND i.is_primary_key = 0 AND i.is_unique_constraint = 0 AND ic.is_included_column = 0
                    GROUP BY t.name, i.name
                """
                try:
                    all_active_rows = execute_query(q_idx) or []
                except Exception:
                    all_active_rows = []

            active_custom_rows = [r for r in all_active_rows if r.get("index_name") not in DEFAULT_SCHEMA_INDEXES]


            matrix = []
            for q in SLOW_QUERIES:
                name = q["name"]
                title = q.get("title", name)
                sql = q["query"]

                latest_base = get_latest_baseline(name)
                baseline_ms = latest_base if (latest_base is not None and latest_base > 0) else None

                if baseline_ms is not None:
                    rec = recommend_index_for_query(sql)
                    target_table = rec.table if rec else ("orders" if "orders" in sql.lower() else "customers")
                    target_cols = set(rec.columns) if rec else set()
                    recommended_sql = rec.create_statement if rec else None
                    reason = rec.reason if rec else ""
                    columns_display = ", ".join(rec.columns) if rec else "-"
                else:
                    target_table = "orders" if "orders" in sql.lower() else "customers"
                    target_cols = set()
                    recommended_sql = None
                    reason = "Trafik simülasyonu bekliyor..."
                    columns_display = "-"

                matching_active_indexes = []
                matching_active_index_sqls = []
                for row in active_custom_rows:
                    tbl = row["table_name"]
                    idx_name = row["index_name"]
                    idx_cols = set([c.strip() for c in row["columns"].split(",")] if row["columns"] else [])

                    if tbl == target_table and ((target_cols and target_cols.issubset(idx_cols)) or (target_cols and target_cols.intersection(idx_cols)) or idx_name in vortex_applied_names):
                        matching_active_indexes.append(idx_name)
                        matching_active_index_sqls.append(f"CREATE NONCLUSTERED INDEX [{idx_name}] ON [{tbl}] ({row['columns']});")

                has_index = len(matching_active_indexes) > 0
                hist = get_benchmark_history(name, 5)

                if not has_index:
                    current_ms = None
                    speedup_pct = None
                    multiplier = None
                    status_label = "Bekliyor"
                elif not hist:
                    current_ms = None
                    speedup_pct = None
                    multiplier = None
                    status_label = "Test Bekliyor"
                else:
                    current_ms = hist[0].mean_ms
                    if baseline_ms and baseline_ms > 0 and current_ms > 0:
                        speedup_pct = round(((baseline_ms - current_ms) / baseline_ms) * 100, 1)
                        multiplier = round(baseline_ms / current_ms, 1) if current_ms > 0 else None
                    else:
                        speedup_pct = None
                        multiplier = None
                    status_label = "İndeksli"

                matrix.append({
                    "name": name,
                    "title": title,
                    "table": target_table,
                    "columns": columns_display,
                    "query_sql": sql,
                    "description": q.get("description", ""),
                    "has_index": has_index,
                    "applied_index_sqls": matching_active_index_sqls,
                    "recommended_sql": recommended_sql,
                    "reason": reason,
                    "baseline_ms": baseline_ms,
                    "current_ms": current_ms,
                    "speedup_pct": speedup_pct,
                    "multiplier": multiplier,
                    "status_label": status_label,
                })
            self.raw_data = matrix

        self.filter_table()

    def filter_table(self):
        search_text = self.search_input.text().lower().strip()
        filtered = []

        for item in self.raw_data:
            matches_search = (
                search_text in item["title"].lower() or
                search_text in item["table"].lower() or
                search_text in item["columns"].lower() or
                search_text in item["query_sql"].lower()
            )
            if not matches_search:
                continue

            if self.filter_mode == "slow" and item["has_index"]:
                continue
            if self.filter_mode == "indexed" and not item["has_index"]:
                continue
            if self.filter_mode == "speedup" and (not item.get("multiplier") or item["multiplier"] <= 1.2):
                continue

            filtered.append(item)

        self.populate_table(filtered)

    def populate_table(self, data):
        self.table.setRowCount(len(data))

        # Dynamically set table height so all rows are listed without an internal scrollbar
        header_height = self.table.horizontalHeader().height()
        if header_height <= 0:
            header_height = 28
        row_height = self.table.verticalHeader().defaultSectionSize() or 52
        total_table_height = header_height + (len(data) * row_height) + 6
        self.table.setFixedHeight(max(total_table_height, 100))

        for row, item in enumerate(data):

            # Col 0: Title & SQL box
            col0_widget = self.create_query_cell(item["title"], item["query_sql"], item["status_label"], item["has_index"])
            self.table.setCellWidget(row, 0, col0_widget)

            # Col 1: Table & Columns
            col1_text = f"{item['table']}\n{item['columns']}"
            col1_item = QTableWidgetItem(col1_text)
            col1_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 1, col1_item)

            # Col 2: Baseline ms
            base = item.get("baseline_ms")
            col2_text = f"{base:.1f} ms" if base is not None else "—"
            col2_item = QTableWidgetItem(col2_text)
            col2_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if base is not None:
                col2_item.setForeground(QColor("#f87171"))
            self.table.setItem(row, 2, col2_item)

            # Col 3: Index Status / DDL
            col3_widget = self.create_index_cell(item["has_index"], item["applied_index_sqls"], item["recommended_sql"])
            self.table.setCellWidget(row, 3, col3_widget)

            # Col 4: Current ms & Speedup
            curr = item.get("current_ms")
            mult = item.get("multiplier")
            if curr is not None:
                if mult and mult > 1:
                    col4_text = f"{curr:.1f} ms  ({mult:.1f}x)"
                else:
                    col4_text = f"{curr:.1f} ms"
            else:
                col4_text = "—"

            col4_item = QTableWidgetItem(col4_text)
            col4_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if mult and mult > 1:
                col4_item.setForeground(QColor("#60a5fa"))
            self.table.setItem(row, 4, col4_item)

    def create_query_cell(self, title: str, sql: str, status_label: str, has_index: bool) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(2)

        # Title row
        title_row = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-weight: 600; color: #f1f5f9; font-size: 11px;")
        title_row.addWidget(title_lbl)

        badge = QLabel(f" {status_label} ")
        if has_index:
            badge.setStyleSheet("background: #0f243d; color: #60a5fa; border: 1px solid #1e40af; border-radius: 3px; font-size: 9.5px; font-weight: 600; padding: 1px 4px;")
        else:
            badge.setStyleSheet("background: #161b24; color: #7f91a5; border: 1px solid #253345; border-radius: 3px; font-size: 9.5px; font-weight: 600; padding: 1px 4px;")
        title_row.addWidget(badge)
        title_row.addStretch()
        layout.addLayout(title_row)

        # SQL box with Copy button
        sql_box = QHBoxLayout()
        sql_box.setSpacing(4)
        sql_lbl = QLabel(sql)
        sql_lbl.setStyleSheet("background: #05080e; border: 1px solid #141f30; border-radius: 4px; padding: 2px 6px; color: #93c5fd; font-family: 'JetBrains Mono', monospace; font-size: 9.5px;")
        sql_box.addWidget(sql_lbl, 1)

        btn_copy = QPushButton("Kopyala")
        btn_copy.setFixedWidth(50)
        btn_copy.setFixedHeight(20)
        btn_copy.setStyleSheet("font-size: 9.5px; padding: 1px 4px; background: #0c1421; border: 1px solid #1c2e46; border-radius: 3px; color: #cbd5e1;")
        btn_copy.clicked.connect(lambda: self.copy_to_clipboard(sql, btn_copy))
        sql_box.addWidget(btn_copy)
        layout.addLayout(sql_box)

        return widget

    def create_index_cell(self, has_index: bool, applied_sqls: list, rec_sql: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(2)

        if has_index and applied_sqls:
            for sql in applied_sqls:
                h_box = QHBoxLayout()
                h_box.setSpacing(4)
                sql_lbl = QLabel(sql)
                sql_lbl.setStyleSheet("background: #0c1828; border: 1px solid #1e3a5f; border-radius: 4px; padding: 2px 6px; color: #93c5fd; font-family: 'JetBrains Mono', monospace; font-size: 9.5px;")
                h_box.addWidget(sql_lbl, 1)

                btn_copy = QPushButton("Kopyala")
                btn_copy.setFixedWidth(50)
                btn_copy.setFixedHeight(20)
                btn_copy.setStyleSheet("font-size: 9.5px; padding: 1px 4px; background: #0c1421; border: 1px solid #1c2e46; border-radius: 3px; color: #cbd5e1;")
                btn_copy.clicked.connect(lambda checked, s=sql, b=btn_copy: self.copy_to_clipboard(s, b))
                h_box.addWidget(btn_copy)
                layout.addLayout(h_box)
        elif rec_sql:
            h_box = QHBoxLayout()
            h_box.setSpacing(4)
            sql_lbl = QLabel(rec_sql)
            sql_lbl.setStyleSheet("background: #090f18; border: 1px solid #1b2d45; border-radius: 4px; padding: 2px 6px; color: #60a5fa; font-family: 'JetBrains Mono', monospace; font-size: 9.5px;")
            h_box.addWidget(sql_lbl, 1)

            btn_copy = QPushButton("Kopyala")
            btn_copy.setFixedWidth(50)
            btn_copy.setFixedHeight(20)
            btn_copy.setStyleSheet("font-size: 9.5px; padding: 1px 4px; background: #0c1421; border: 1px solid #1c2e46; border-radius: 3px; color: #cbd5e1;")
            btn_copy.clicked.connect(lambda checked, s=rec_sql, b=btn_copy: self.copy_to_clipboard(s, b))
            h_box.addWidget(btn_copy)
            layout.addLayout(h_box)
        else:
            lbl = QLabel("Henüz öneri oluşturulmadı")
            lbl.setStyleSheet("color: #55697f; font-size: 9.5px;")
            layout.addWidget(lbl)

        return widget

    def copy_to_clipboard(self, text: str, btn: QPushButton):
        QApplication.clipboard().setText(text)
        btn.setText("Kopyalandı")
        btn.setStyleSheet("font-size: 9.5px; padding: 1px 4px; background: #1d4ed8; color: #ffffff; border: 1px solid #3b82f6; border-radius: 3px;")

