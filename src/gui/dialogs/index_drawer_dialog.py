"""Index Drawer Dialog for Applied and Unused Indexes."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
    QMessageBox,
    QApplication,
)
from PyQt6.QtCore import Qt
import qtawesome as qta

try:
    from src.state_store import get_active_indexes, record_index_rolled_back
    from src.pg_stats_reader import get_index_stats
    from src.unused_index_detector import get_unused_indexes
    from src.db_connection import execute_query
except ImportError:
    from state_store import get_active_indexes, record_index_rolled_back
    from pg_stats_reader import get_index_stats
    from unused_index_detector import get_unused_indexes
    from db_connection import execute_query


class IndexDrawerDialog(QDialog):
    """Slide-over style Index Management Dialog."""
    def __init__(self, active_tab: str = "applied", parent=None):
        super().__init__(parent)
        self.setWindowTitle("SQL Server İndeks Çekmecesi")
        self.resize(780, 560)
        self.setModal(True)

        self.init_ui(active_tab)
        self.load_data()

    def init_ui(self, initial_tab: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        header_row = QHBoxLayout()
        icon_lbl = QLabel()
        try:
            icon_lbl.setPixmap(qta.icon("fa5s.layer-group", color="#34d399").pixmap(24, 24))
        except Exception:
            pass
        header_row.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        title_lbl = QLabel("SQL Server İndeks Çekmecesi")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        sub_lbl = QLabel("Özel uygulanan optimizasyon indeksleri ve atıl/şişkinlik analizleri")
        sub_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(sub_lbl)
        header_row.addLayout(title_vbox)
        header_row.addStretch()
        layout.addLayout(header_row)

        # Tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Applied Indexes
        self.tab_applied = QWidget()
        tab_applied_layout = QVBoxLayout(self.tab_applied)
        tab_applied_layout.setContentsMargins(8, 12, 8, 8)
        
        self.table_applied = QTableWidget()
        self.table_applied.setColumnCount(4)
        self.table_applied.setHorizontalHeaderLabels(["İndeks Adı", "Hedef Tablo", "DMV Taraması", "Oluşturma DDL"])
        self.table_applied.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_applied.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_applied.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_applied.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        tab_applied_layout.addWidget(self.table_applied)
        self.tabs.addTab(self.tab_applied, "⚡ Uygulanan Özel İndeksler")

        # Tab 2: Unused Indexes
        self.tab_unused = QWidget()
        tab_unused_layout = QVBoxLayout(self.tab_unused)
        tab_unused_layout.setContentsMargins(8, 12, 8, 8)
        
        self.table_unused = QTableWidget()
        self.table_unused.setColumnCount(5)
        self.table_unused.setHorizontalHeaderLabels(["İndeks Adı", "Tablo", "Kategori", "Gerekçe", "İşlem"])
        self.table_unused.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_unused.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_unused.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_unused.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_unused.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table_unused.setColumnWidth(4, 100)
        tab_unused_layout.addWidget(self.table_unused)
        self.tabs.addTab(self.tab_unused, "⚠️ Atıl / Gereksiz İndeksler")

        layout.addWidget(self.tabs)

        if initial_tab == "unused":
            self.tabs.setCurrentIndex(1)

        # Footer close button
        footer_row = QHBoxLayout()
        footer_row.addStretch()
        self.btn_close = QPushButton("Kapat")
        self.btn_close.clicked.connect(self.accept)
        footer_row.addWidget(self.btn_close)
        layout.addLayout(footer_row)

    def load_data(self):
        # 1. Load Applied Indexes
        active_idx = get_active_indexes()
        idx_stats = {s.indexrelname: s for s in get_index_stats()}
        
        self.table_applied.setRowCount(len(active_idx))
        for row, item in enumerate(active_idx):
            name = item.index_name
            table = item.table_name
            ddl = item.create_sql
            stats = idx_stats.get(name)
            scans = stats.idx_scan if stats else 0

            name_item = QTableWidgetItem(name)
            name_item.setForeground(Qt.GlobalColor.cyan)
            self.table_applied.setItem(row, 0, name_item)

            table_item = QTableWidgetItem(table)
            self.table_applied.setItem(row, 1, table_item)

            scans_item = QTableWidgetItem(f"{scans} Tarama")
            scans_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_applied.setItem(row, 2, scans_item)

            ddl_item = QTableWidgetItem(ddl)
            ddl_item.setToolTip("Kopyalamak için tıklayın")
            self.table_applied.setItem(row, 3, ddl_item)

        # 2. Load Unused Indexes
        unused_list = get_unused_indexes()
        self.table_unused.setRowCount(len(unused_list))
        for row, item in enumerate(unused_list):
            name = item.index_name
            table = item.table_name
            cat = "Atıl / 0 Tarama"
            reason = f"{item.index_size_pretty} alan kaplıyor ancak hiç aranmadı."

            name_item = QTableWidgetItem(name)
            name_item.setForeground(Qt.GlobalColor.red)
            self.table_unused.setItem(row, 0, name_item)

            table_item = QTableWidgetItem(table)
            self.table_unused.setItem(row, 1, table_item)

            cat_item = QTableWidgetItem(cat)
            self.table_unused.setItem(row, 2, cat_item)

            reason_item = QTableWidgetItem(reason)
            self.table_unused.setItem(row, 3, reason_item)

            # Drop button
            btn_drop = QPushButton("🗑 Sil (Drop)")
            btn_drop.setProperty("class", "btn-danger")
            btn_drop.clicked.connect(lambda checked, n=name, t=table: self.drop_index(n, t))
            self.table_unused.setCellWidget(row, 4, btn_drop)

    def drop_index(self, index_name: str, table_name: str):
        reply = QMessageBox.question(
            self,
            "İndeks Silme Onayı",
            f"[{index_name}] indeksi [{table_name}] tablosundan kaldırılacaktır. Onaylıyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                execute_query(f"DROP INDEX [{index_name}] ON [{table_name}];")
                record_index_rolled_back(index_name)
                QMessageBox.information(self, "Silindi", f"[{index_name}] indeksi başarıyla silindi.")
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"İndeks silinemedi: {e}")
