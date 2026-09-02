"""Main Application Window for VortexDBA native PyQt6 desktop software."""

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QFrame,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QMessageBox,
    QStatusBar,
)
from PyQt6.QtCore import Qt, QTimer
import qtawesome as qta

try:
    from src.config import get_config, update_operating_mode, update_traffic_source
    from src.state_store import get_active_indexes, get_latest_baseline
    from src.gui.theme import DARK_THEME_QSS
    from src.gui.widgets.stat_card import StatCard
    from src.gui.widgets.performance_table import PerformanceMatrixWidget
    from src.gui.dialogs.db_config_dialog import DbConfigDialog
    from src.gui.dialogs.index_drawer_dialog import IndexDrawerDialog
    from src.gui.workers import (
        SimulateWorker,
        RemediateWorker,
        BenchmarkWorker,
        ResetWorker,
    )
except ImportError:
    from config import get_config, update_operating_mode, update_traffic_source
    from state_store import get_active_indexes, get_latest_baseline
    from gui.theme import DARK_THEME_QSS
    from gui.widgets.stat_card import StatCard
    from gui.widgets.performance_table import PerformanceMatrixWidget
    from gui.dialogs.db_config_dialog import DbConfigDialog
    from gui.dialogs.index_drawer_dialog import IndexDrawerDialog
    from gui.workers import (
        SimulateWorker,
        RemediateWorker,
        BenchmarkWorker,
        ResetWorker,
    )


class MainWindow(QMainWindow):
    """Main window for VortexDBA native desktop application."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VortexDBA - Autonomous AI Database Optimization Engine")
        self.resize(1420, 920)
        self.setMinimumSize(1080, 720)

        self.current_worker = None

        # Apply QSS Dark Theme
        self.setStyleSheet(DARK_THEME_QSS)

        self.init_ui()
        self.refresh_all()

        # Periodic auto-refresh every 30 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.auto_refresh)
        self.timer.start(30000)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Header Bar
        header_frame = QFrame()
        header_frame.setProperty("class", "header-panel")
        header_frame.setFixedHeight(54)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 0, 20, 0)
        header_layout.setSpacing(12)

        # Brand Logo
        brand_box = QHBoxLayout()
        logo_lbl = QLabel()
        try:
            logo_lbl.setPixmap(qta.icon("fa5s.bolt", color="#38bdf8").pixmap(20, 20))
        except Exception:
            pass
        brand_box.addWidget(logo_lbl)

        brand_lbl = QLabel("VORTEX//DBA")
        brand_lbl.setStyleSheet("font-size: 15px; font-weight: 900; color: #ffffff; letter-spacing: 0.5px;")
        brand_box.addWidget(brand_lbl)

        tag_lbl = QLabel("Masaüstü v2.4")
        tag_lbl.setStyleSheet("background: rgba(56, 189, 248, 0.1); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: 700;")
        brand_box.addWidget(tag_lbl)
        header_layout.addLayout(brand_box)

        header_layout.addStretch()

        # Center Database Pill Button
        self.btn_db_capsule = QPushButton()
        self.btn_db_capsule.setStyleSheet("""
            QPushButton {
                background: #0b111e;
                border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 16px;
                padding: 6px 16px;
                color: #e2e8f0;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                border-color: #38bdf8;
                background: #111a2d;
                color: #ffffff;
            }
        """)
        try:
            self.btn_db_capsule.setIcon(qta.icon("fa5s.database", color="#38bdf8"))
        except Exception:
            pass
        self.btn_db_capsule.clicked.connect(self.open_db_dialog)
        header_layout.addWidget(self.btn_db_capsule)

        header_layout.addStretch()

        # Right Controls
        # Mode switch (Mod A vs Mod B)
        mode_box = QFrame()
        mode_box.setStyleSheet("background: #080c14; border: 1px solid #1e293b; border-radius: 8px; padding: 2px;")
        mode_layout = QHBoxLayout(mode_box)
        mode_layout.setContentsMargins(2, 2, 2, 2)
        mode_layout.setSpacing(2)

        self.btn_mode_a = QPushButton("👤 Mod A (Danışman)")
        self.btn_mode_a.setProperty("class", "segment-btn")
        self.btn_mode_a.setCheckable(True)
        self.btn_mode_a.clicked.connect(lambda: self.switch_mode("advisor"))
        mode_layout.addWidget(self.btn_mode_a)

        self.btn_mode_b = QPushButton("🤖 Mod B (Otopilot)")
        self.btn_mode_b.setProperty("class", "segment-btn")
        self.btn_mode_b.setCheckable(True)
        self.btn_mode_b.clicked.connect(lambda: self.switch_mode("autonomous"))
        mode_layout.addWidget(self.btn_mode_b)
        header_layout.addWidget(mode_box)

        # Source switch (Sim vs Live DMV)
        source_box = QFrame()
        source_box.setStyleSheet("background: #080c14; border: 1px solid #1e293b; border-radius: 8px; padding: 2px;")
        source_layout = QHBoxLayout(source_box)
        source_layout.setContentsMargins(2, 2, 2, 2)
        source_layout.setSpacing(2)

        self.btn_src_sim = QPushButton("🧪 Simülasyon")
        self.btn_src_sim.setProperty("class", "segment-btn")
        self.btn_src_sim.setCheckable(True)
        self.btn_src_sim.clicked.connect(lambda: self.switch_source("simulation"))
        source_layout.addWidget(self.btn_src_sim)

        self.btn_src_live = QPushButton("🔴 Canlı DMV")
        self.btn_src_live.setProperty("class", "segment-btn")
        self.btn_src_live.setCheckable(True)
        self.btn_src_live.clicked.connect(lambda: self.switch_source("live_dmv"))
        source_layout.addWidget(self.btn_src_live)
        header_layout.addWidget(source_box)

        # Index Drawer button
        self.btn_drawer = QPushButton("İndeksler")
        try:
            self.btn_drawer.setIcon(qta.icon("fa5s.layer-group", color="#34d399"))
        except Exception:
            pass
        self.btn_drawer.clicked.connect(self.open_index_drawer)
        header_layout.addWidget(self.btn_drawer)

        # Refresh button
        self.btn_refresh = QPushButton()
        self.btn_refresh.setFixedWidth(36)
        try:
            self.btn_refresh.setIcon(qta.icon("fa5s.sync-alt", color="#94a3b8"))
        except Exception:
            self.btn_refresh.setText("↺")
        self.btn_refresh.clicked.connect(self.refresh_all)
        header_layout.addWidget(self.btn_refresh)

        root_layout.addWidget(header_frame)

        # 2. Scrollable Body Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(24, 18, 24, 24)
        self.content_layout.setSpacing(16)

        # Autopilot Banner (Visible in Mode B)
        self.autopilot_banner = QFrame()
        self.autopilot_banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(52, 211, 153, 0.15), stop:1 rgba(56, 189, 248, 0.05));
                border: 1px solid rgba(52, 211, 153, 0.3);
                border-radius: 10px;
                padding: 10px;
            }
        """)
        banner_layout = QHBoxLayout(self.autopilot_banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)
        self.banner_lbl = QLabel("🤖 OTOPİLOT MODU (Mod B) DEVREDE: SQL Server 7/24 arka planda izlenir, eksik indeksler ONLINE=ON ile otomatik uygulanır ve yavaşlama olursa rollback yapılır.")
        self.banner_lbl.setStyleSheet("color: #34d399; font-weight: 700; font-size: 12px;")
        banner_layout.addWidget(self.banner_lbl)
        banner_layout.addStretch()
        self.btn_switch_to_advisor = QPushButton("Danışman Moduna Geç")
        self.btn_switch_to_advisor.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        self.btn_switch_to_advisor.clicked.connect(lambda: self.switch_mode("advisor"))
        banner_layout.addWidget(self.btn_switch_to_advisor)
        self.content_layout.addWidget(self.autopilot_banner)

        # 3. 5-Step Command Deck (Workflow Toolbar)
        command_deck = QFrame()
        command_deck.setProperty("class", "card-panel")
        deck_layout = QHBoxLayout(command_deck)
        deck_layout.setContentsMargins(18, 14, 18, 14)
        deck_layout.setSpacing(10)

        deck_title = QLabel("OTONOM DBA AKIŞI:")
        deck_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #38bdf8; letter-spacing: 0.5px;")
        deck_layout.addWidget(deck_title)

        self.btn_step1 = QPushButton("1. 🧪 Yavaş Trafik Simüle Et")
        self.btn_step1.setToolTip("15 yavaş T-SQL sorgusunu koşturup indeks öncesi baseline sürelerini kaydeder")
        self.btn_step1.clicked.connect(self.run_step1)
        deck_layout.addWidget(self.btn_step1)

        self.btn_step2 = QPushButton("2. ⚡ İndeksleri Otomatik Uygula")
        self.btn_step2.setProperty("class", "btn-success")
        self.btn_step2.setToolTip("IndexAdvisor DDL önerilerini ONLINE=ON ile SQL Server'a otomatik uygular")
        self.btn_step2.clicked.connect(self.run_step2)
        deck_layout.addWidget(self.btn_step2)

        self.btn_step3 = QPushButton("3. 📊 Canlı Benchmark Testi")
        self.btn_step3.setProperty("class", "btn-warning")
        self.btn_step3.setToolTip("Canlı 3-iterasyonlu kıyaslama testi çalıştırıp hızlanma çarpanını hesaplar")
        self.btn_step3.clicked.connect(self.run_step3)
        deck_layout.addWidget(self.btn_step3)

        self.btn_step4 = QPushButton("4. ↺ İndeksleri Sıfırla")
        self.btn_step4.setToolTip("SQL Server üzerindeki tüm özel optimizasyon indekslerini siler")
        self.btn_step4.clicked.connect(self.run_step4)
        deck_layout.addWidget(self.btn_step4)

        self.btn_step5 = QPushButton("5. 💥 Fabrika Ayarları")
        self.btn_step5.setProperty("class", "btn-danger")
        self.btn_step5.setToolTip("Özel indeksleri, baseline ölçümlerini ve karar geçmişini sıfırlar")
        self.btn_step5.clicked.connect(self.run_step5)
        deck_layout.addWidget(self.btn_step5)

        self.content_layout.addWidget(command_deck)

        # 4. 4 Stat Metrics Cards
        metrics_grid = QHBoxLayout()
        metrics_grid.setSpacing(14)
        self.card_indexes = StatCard("Aktif Özel İndeksler", "0", "/ 15 Kapsandı", "fa5s.layer-group", "#34d399")
        metrics_grid.addWidget(self.card_indexes)

        self.card_speedup = StatCard("Ortalama Hızlanma", "—", "3. Adım sonrası ölçülür", "fa5s.chart-line", "#38bdf8")
        metrics_grid.addWidget(self.card_speedup)

        self.card_critical = StatCard("Kritik Yavaş Sorgular", "0", ">400ms darboğaz", "fa5s.exclamation-triangle", "#fbbf24")
        metrics_grid.addWidget(self.card_critical)

        self.card_safety = StatCard("Güvenlik & Rollback", "%100", "ONLINE=ON Zero-Lock", "fa5s.shield-alt", "#818cf8")
        metrics_grid.addWidget(self.card_safety)
        self.content_layout.addLayout(metrics_grid)

        # 5. Real-Time Streaming Terminal Log Box
        terminal_frame = QFrame()
        terminal_frame.setProperty("class", "card-panel")
        term_layout = QVBoxLayout(terminal_frame)
        term_layout.setContentsMargins(14, 10, 14, 12)
        term_layout.setSpacing(8)

        term_topbar = QHBoxLayout()
        term_title = QLabel("CANLI LOG AKIŞI & REALTIME TRACE")
        term_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px;")
        term_topbar.addWidget(term_title)
        term_topbar.addStretch()

        self.term_status_lbl = QLabel("READY")
        self.term_status_lbl.setStyleSheet("color: #34d399; font-weight: 800; font-size: 10.5px; font-family: 'JetBrains Mono', monospace;")
        term_topbar.addWidget(self.term_status_lbl)

        btn_clear_term = QPushButton("Temizle")
        btn_clear_term.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        btn_clear_term.clicked.connect(lambda: self.terminal_box.clear())
        term_topbar.addWidget(btn_clear_term)
        term_layout.addLayout(term_topbar)

        self.terminal_box = QPlainTextEdit()
        self.terminal_box.setReadOnly(True)
        self.terminal_box.setFixedHeight(160)
        self.terminal_box.setPlaceholderText("[Hazır] SQL Server optimizasyon ve benchmark akışları burada canlı gösterilir...")
        term_layout.addWidget(self.terminal_box)
        self.content_layout.addWidget(terminal_frame)

        # 6. Performance Matrix Table Widget
        self.matrix_widget = PerformanceMatrixWidget()
        self.content_layout.addWidget(self.matrix_widget)

        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll)

        # Status Bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("VortexDBA Masaüstü Motoru Hazır.")

    def update_header_state(self):
        cfg = get_config()
        # Update DB Capsule text
        db = cfg.database
        self.btn_db_capsule.setText(f"  {db.host}:{db.port} [{db.dbname}]  ")

        # Update Mode buttons
        is_auto = (getattr(cfg, "operating_mode", "advisor") == "autonomous")
        self.btn_mode_a.setChecked(not is_auto)
        self.btn_mode_b.setChecked(is_auto)
        self.autopilot_banner.setVisible(is_auto)

        # Update Source buttons
        is_live = (getattr(cfg, "traffic_source", "simulation") == "live_dmv")
        self.btn_src_sim.setChecked(not is_live)
        self.btn_src_live.setChecked(is_live)

    def refresh_all(self):
        self.update_header_state()
        self.matrix_widget.load_data()
        self.update_metrics()
        self.statusBar().showMessage("Paneller güncellendi.")

    def auto_refresh(self):
        if not self.current_worker or not self.current_worker.isRunning():
            self.refresh_all()

    def update_metrics(self):
        active_indexes = get_active_indexes()
        idx_count = len(active_indexes)
        self.card_indexes.set_value(str(idx_count), f"/ 15 Kapsandı")

        matrix = self.matrix_widget.raw_data
        multipliers = [m["multiplier"] for m in matrix if m.get("multiplier") and m["multiplier"] > 1]
        if multipliers:
            avg_mult = sum(multipliers) / len(multipliers)
            self.card_speedup.set_value(f"{avg_mult:.1f}x", "Daha Hızlı")
        else:
            self.card_speedup.set_value("—", "3. Adım sonrası ölçülür")

        critical = len([m for m in matrix if not m.get("has_index") and (m.get("baseline_ms") or 0) > 400])
        self.card_critical.set_value(str(critical), "Kritik darboğaz" if critical > 0 else "✔ Tüm sorgular kabul edilebilir")

    def switch_mode(self, mode: str):
        update_operating_mode(mode)
        self.refresh_all()

    def switch_source(self, source: str):
        update_traffic_source(source)
        self.refresh_all()

    def open_db_dialog(self):
        dlg = DbConfigDialog(self)
        if dlg.exec():
            self.refresh_all()

    def open_index_drawer(self):
        dlg = IndexDrawerDialog("applied", self)
        dlg.exec()
        self.refresh_all()

    def set_running_state(self, running: bool):
        self.btn_step1.setEnabled(not running)
        self.btn_step2.setEnabled(not running)
        self.btn_step3.setEnabled(not running)
        self.btn_step4.setEnabled(not running)
        self.btn_step5.setEnabled(not running)
        self.term_status_lbl.setText("RUNNING..." if running else "COMPLETED")
        self.term_status_lbl.setStyleSheet("color: #fbbf24;" if running else "color: #34d399;")

    def append_log(self, text: str):
        self.terminal_box.appendPlainText(text)
        self.terminal_box.verticalScrollBar().setValue(self.terminal_box.verticalScrollBar().maximum())

    def on_worker_finished(self, success: bool, msg: str):
        self.set_running_state(False)
        self.refresh_all()

    def run_step1(self):
        self.set_running_state(True)
        self.current_worker = SimulateWorker()
        self.current_worker.log_signal.connect(self.append_log)
        self.current_worker.finished_signal.connect(self.on_worker_finished)
        self.current_worker.start()

    def run_step2(self):
        self.set_running_state(True)
        self.current_worker = RemediateWorker()
        self.current_worker.log_signal.connect(self.append_log)
        self.current_worker.finished_signal.connect(self.on_worker_finished)
        self.current_worker.start()

    def run_step3(self):
        self.set_running_state(True)
        self.current_worker = BenchmarkWorker()
        self.current_worker.log_signal.connect(self.append_log)
        self.current_worker.finished_signal.connect(self.on_worker_finished)
        self.current_worker.start()

    def run_step4(self):
        reply = QMessageBox.question(
            self,
            "İndeksleri Sıfırlama",
            "SQL Server üzerindeki tüm özel optimizasyon indeksleri kaldırılacaktır. Onaylıyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.set_running_state(True)
            self.current_worker = ResetWorker(full_reset=False)
            self.current_worker.log_signal.connect(self.append_log)
            self.current_worker.finished_signal.connect(self.on_worker_finished)
            self.current_worker.start()

    def run_step5(self):
        reply = QMessageBox.warning(
            self,
            "Fabrika Sıfırlaması",
            "DİKKAT: Tüm özel indeksler, baseline ölçümleri ve karar geçmişi tamamen silinip fabrika ayarlarına dönülecektir. Onaylıyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.set_running_state(True)
            self.current_worker = ResetWorker(full_reset=True)
            self.current_worker.log_signal.connect(self.append_log)
            self.current_worker.finished_signal.connect(self.on_worker_finished)
            self.current_worker.start()
