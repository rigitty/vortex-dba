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
    QSplitter,
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
        DbQuickCheckWorker,
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
        DbQuickCheckWorker,
    )


from pathlib import Path
from PyQt6.QtGui import QIcon

class MainWindow(QMainWindow):
    """Main window for VortexDBA native desktop application."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VortexDBA")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.resize(1420, 920)
        self.setMinimumSize(1080, 720)

        self._drag_pos = None

        # Load application logo
        logo_path = Path(__file__).resolve().parent.parent.parent / "logo.svg"
        if not logo_path.exists():
            logo_path = Path.cwd() / "logo.svg"
        self.logo_path = logo_path
        if self.logo_path.exists():
            self.setWindowIcon(QIcon(str(self.logo_path)))

        self.current_worker = None
        self.check_worker = None
        self.is_connected = False
        self.conn_latency = None

        # Apply QSS Dark Theme
        self.setStyleSheet(DARK_THEME_QSS)

        self.init_ui()
        self.refresh_all()

        # Heartbeat timer (only monitors liveness when already connected)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.auto_refresh)
        self.timer.start(3000)

    def toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        if self.isMaximized():
            self.showNormal()
            self.btn_max.setText("🗖")
        else:
            self.showMaximized()
            self.btn_max.setText("🗗")

    def eventFilter(self, obj, event):
        """Handle custom window dragging and double-click maximizing on the header."""
        if obj == getattr(self, "header_frame", None):
            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    return False
            elif event.type() == event.Type.MouseMove:
                if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
                    if self.isMaximized():
                        self.showNormal()
                        self.btn_max.setText("🗖")
                    self.move(event.globalPosition().toPoint() - self._drag_pos)
                    return True
            elif event.type() == event.Type.MouseButtonRelease:
                self._drag_pos = None
            elif event.type() == event.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.toggle_maximize()
                    return True
        return super().eventFilter(obj, event)

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Custom Top Title & Header Bar
        self.header_frame = QFrame()
        self.header_frame.setProperty("class", "header-panel")
        self.header_frame.setFixedHeight(42)
        self.header_frame.installEventFilter(self)

        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(12, 0, 8, 0)
        header_layout.setSpacing(10)

        # Brand Logo & Title
        brand_box = QHBoxLayout()
        brand_box.setSpacing(10)
        logo_lbl = QLabel()
        if self.logo_path.exists():
            logo_pix = QIcon(str(self.logo_path)).pixmap(22, 22)
            logo_lbl.setPixmap(logo_pix)
        else:
            try:
                logo_lbl.setPixmap(qta.icon("fa5s.bolt", color="#06b6d4").pixmap(20, 20))
            except Exception:
                pass
        brand_box.addWidget(logo_lbl)

        brand_lbl = QLabel("VORTEX DBA")
        brand_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #ffffff; letter-spacing: 0.8px; font-family: 'JetBrains Mono', 'Segoe UI', sans-serif;")
        brand_box.addWidget(brand_lbl)
        header_layout.addLayout(brand_box)

        header_layout.addStretch()

        # Center Database Pill Button
        self.btn_db_capsule = QPushButton()
        self.btn_db_capsule.setToolTip("SQL Server bağlantı durumunu görmek ve ayarları düzenlemek için tıklayın")
        self.btn_db_capsule.clicked.connect(self.open_db_dialog)
        header_layout.addWidget(self.btn_db_capsule)

        # Quick Connect Header Button
        self.btn_connect_header = QPushButton("Sunucuya Bağlan")
        self.btn_connect_header.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                border: 1px solid #3b82f6;
                color: #ffffff;
                font-weight: 600;
                font-size: 10.5px;
                padding: 4px 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
        """)
        self.btn_connect_header.clicked.connect(self.open_db_dialog)
        header_layout.addWidget(self.btn_connect_header)

        header_layout.addStretch()

        # Right Controls
        # Mode switch (Mod A vs Mod B)
        mode_box = QFrame()
        mode_box.setStyleSheet("background: #080d16; border: 1px solid #162234; border-radius: 5px; padding: 1px;")
        mode_layout = QHBoxLayout(mode_box)
        mode_layout.setContentsMargins(2, 2, 2, 2)
        mode_layout.setSpacing(2)

        self.btn_mode_a = QPushButton("Mod A (Danışman)")
        self.btn_mode_a.setProperty("class", "segment-btn")
        self.btn_mode_a.setCheckable(True)
        self.btn_mode_a.clicked.connect(lambda: self.switch_mode("advisor"))
        mode_layout.addWidget(self.btn_mode_a)

        self.btn_mode_b = QPushButton("Mod B (Otopilot)")
        self.btn_mode_b.setProperty("class", "segment-btn")
        self.btn_mode_b.setCheckable(True)
        self.btn_mode_b.clicked.connect(lambda: self.switch_mode("autonomous"))
        mode_layout.addWidget(self.btn_mode_b)
        header_layout.addWidget(mode_box)

        # Source switch (Sim vs Live DMV)
        source_box = QFrame()
        source_box.setStyleSheet("background: #080d16; border: 1px solid #162234; border-radius: 5px; padding: 1px;")
        source_layout = QHBoxLayout(source_box)
        source_layout.setContentsMargins(2, 2, 2, 2)
        source_layout.setSpacing(2)

        self.btn_src_sim = QPushButton("Simülasyon")
        self.btn_src_sim.setProperty("class", "segment-btn")
        self.btn_src_sim.setCheckable(True)
        self.btn_src_sim.clicked.connect(lambda: self.switch_source("simulation"))
        source_layout.addWidget(self.btn_src_sim)

        self.btn_src_live = QPushButton("Canlı DMV")
        self.btn_src_live.setProperty("class", "segment-btn")
        self.btn_src_live.setCheckable(True)
        self.btn_src_live.clicked.connect(lambda: self.switch_source("live_dmv"))
        source_layout.addWidget(self.btn_src_live)
        header_layout.addWidget(source_box)

        # Index Drawer button
        self.btn_drawer = QPushButton("İndeksler")
        try:
            self.btn_drawer.setIcon(qta.icon("fa5s.layer-group", color="#60a5fa"))
        except Exception:
            pass
        self.btn_drawer.clicked.connect(self.open_index_drawer)
        header_layout.addWidget(self.btn_drawer)

        # Refresh button
        self.btn_refresh = QPushButton()
        self.btn_refresh.setFixedWidth(30)
        self.btn_refresh.setFixedHeight(26)
        try:
            self.btn_refresh.setIcon(qta.icon("fa5s.sync-alt", color="#94a3b8"))
        except Exception:
            self.btn_refresh.setText("↺")
        self.btn_refresh.clicked.connect(self.refresh_all)
        header_layout.addWidget(self.btn_refresh)

        # Separator line before window controls
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #1e293b; background: #1e293b; max-width: 1px; margin: 8px 3px;")
        header_layout.addWidget(sep)

        # Custom Window Control Buttons (Minimize, Maximize/Restore, Close)
        win_controls = QHBoxLayout()
        win_controls.setSpacing(3)
        win_controls.setContentsMargins(0, 0, 0, 0)

        self.btn_min = QPushButton("🗕")
        self.btn_min.setFixedSize(28, 26)
        self.btn_min.setToolTip("Simge Durumuna Küçült")
        self.btn_min.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid transparent;
                color: #94a3b8;
                font-size: 11px;
                border-radius: 4px;
                padding: 0;
            }
            QPushButton:hover {
                background: #111d33;
                border: 1px solid #1e3a5f;
                color: #ffffff;
            }
        """)
        self.btn_min.clicked.connect(self.showMinimized)
        win_controls.addWidget(self.btn_min)

        self.btn_max = QPushButton("🗖")
        self.btn_max.setFixedSize(28, 26)
        self.btn_max.setToolTip("Ekranı Kapla / Geri Yükle")
        self.btn_max.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid transparent;
                color: #94a3b8;
                font-size: 11px;
                border-radius: 4px;
                padding: 0;
            }
            QPushButton:hover {
                background: #111d33;
                border: 1px solid #1e3a5f;
                color: #ffffff;
            }
        """)
        self.btn_max.clicked.connect(self.toggle_maximize)
        win_controls.addWidget(self.btn_max)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(28, 26)
        self.btn_close.setToolTip("Kapat")
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid transparent;
                color: #94a3b8;
                font-size: 11px;
                font-weight: 700;
                border-radius: 4px;
                padding: 0;
            }
            QPushButton:hover {
                background: #dc2626;
                border: 1px solid #ef4444;
                color: #ffffff;
            }
        """)
        self.btn_close.clicked.connect(self.close)
        win_controls.addWidget(self.btn_close)

        header_layout.addLayout(win_controls)

        root_layout.addWidget(self.header_frame)


        # 2. Scrollable Body Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(14, 12, 14, 14)
        self.content_layout.setSpacing(10)

        # Offline Warning Banner (Visible when DB is disconnected)
        self.offline_banner = QFrame()
        self.offline_banner.setStyleSheet("""
            QFrame {
                background: #140d12;
                border: 1px solid #4a161f;
                border-radius: 5px;
                padding: 4px;
            }
        """)
        off_layout = QHBoxLayout(self.offline_banner)
        off_layout.setContentsMargins(10, 6, 10, 6)
        off_layout.setSpacing(10)

        self.off_lbl = QLabel("SQL Server bağlantısı kurulamadı. Uygulama çevrimdışı modda çalışıyor.")
        self.off_lbl.setStyleSheet("color: #fca5a5; font-weight: 600; font-size: 10.5px;")
        off_layout.addWidget(self.off_lbl, 1)

        btn_banner_connect = QPushButton("Bağlan")
        btn_banner_connect.setStyleSheet("font-size: 10px; padding: 3px 8px; background: #991b1b; border: 1px solid #dc2626; color: white; font-weight: 600; border-radius: 4px;")
        btn_banner_connect.clicked.connect(self.open_db_dialog)
        off_layout.addWidget(btn_banner_connect)

        btn_banner_retry = QPushButton("Yeniden Dene")
        btn_banner_retry.setStyleSheet("font-size: 10px; padding: 3px 8px; background: #131a26; border: 1px solid #1e2c40; color: #cbd5e1; border-radius: 4px;")
        btn_banner_retry.clicked.connect(lambda: self.trigger_connection_check(show_connecting=True))
        off_layout.addWidget(btn_banner_retry)


        self.content_layout.addWidget(self.offline_banner)

        # Autopilot Banner (Visible in Mode B)
        self.autopilot_banner = QFrame()
        self.autopilot_banner.setStyleSheet("""
            QFrame {
                background: #091322;
                border: 1px solid #1e3a5f;
                border-radius: 5px;
                padding: 4px;
            }
        """)
        banner_layout = QHBoxLayout(self.autopilot_banner)
        banner_layout.setContentsMargins(10, 6, 10, 6)
        self.banner_lbl = QLabel("OTOPİLOT MODU AKTİF: SQL Server 7/24 izlenir, indeksler ONLINE=ON ile otomatik uygulanır.")
        self.banner_lbl.setStyleSheet("color: #93c5fd; font-weight: 600; font-size: 10.5px;")
        banner_layout.addWidget(self.banner_lbl)
        banner_layout.addStretch()
        self.btn_switch_to_advisor = QPushButton("Danışman Moduna Geç")
        self.btn_switch_to_advisor.setStyleSheet("font-size: 10px; padding: 3px 8px; background: #101e33; border: 1px solid #203c66; color: #60a5fa; border-radius: 4px;")
        self.btn_switch_to_advisor.clicked.connect(lambda: self.switch_mode("advisor"))
        banner_layout.addWidget(self.btn_switch_to_advisor)
        self.content_layout.addWidget(self.autopilot_banner)

        # 3. 5-Step Command Deck (Workflow Toolbar)
        command_deck = QFrame()
        command_deck.setProperty("class", "card-panel")
        deck_layout = QHBoxLayout(command_deck)
        deck_layout.setContentsMargins(12, 8, 12, 8)
        deck_layout.setSpacing(8)

        deck_title = QLabel("AKIŞ:")
        deck_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #60a5fa; letter-spacing: 0.5px;")
        deck_layout.addWidget(deck_title)

        self.btn_step1 = QPushButton("1. Trafik Simülasyonu")
        self.btn_step1.setToolTip("15 adet yavaş T-SQL sorgusunu koşturup baseline sürelerini kaydeder")
        self.btn_step1.clicked.connect(self.run_step1)
        deck_layout.addWidget(self.btn_step1)

        self.btn_step2 = QPushButton("2. İndeks Oluştur")
        self.btn_step2.setProperty("class", "btn-primary")
        self.btn_step2.setToolTip("Önerilen tüm indeksleri SQL Server üzerinde ONLINE=ON ile oluşturur")
        self.btn_step2.clicked.connect(self.run_step2)
        deck_layout.addWidget(self.btn_step2)


        self.btn_step3 = QPushButton("3. Benchmark Testi")
        self.btn_step3.setProperty("class", "btn-secondary")
        self.btn_step3.setToolTip("İndeks öncesi vs sonrası kıyaslama testi çalıştırır")
        self.btn_step3.clicked.connect(self.run_step3)
        deck_layout.addWidget(self.btn_step3)

        self.btn_step4 = QPushButton("4. İndeksleri Sıfırla")
        self.btn_step4.setToolTip("Özel optimizasyon indekslerini kaldırır")
        self.btn_step4.clicked.connect(self.run_step4)
        deck_layout.addWidget(self.btn_step4)

        self.btn_step5 = QPushButton("5. Fabrika Sıfırla")
        self.btn_step5.setProperty("class", "btn-danger")
        self.btn_step5.setToolTip("Tüm özel indeksleri ve ölçüm geçmişini sıfırlar")
        self.btn_step5.clicked.connect(self.run_step5)
        deck_layout.addWidget(self.btn_step5)

        self.content_layout.addWidget(command_deck)

        # 4. 4 Stat Metrics Cards
        metrics_grid = QHBoxLayout()
        metrics_grid.setSpacing(8)
        self.card_indexes = StatCard("Özel İndeksler", "0", "/ 15 Kapsandı", "fa5s.layer-group", "#3b82f6")
        metrics_grid.addWidget(self.card_indexes)

        self.card_speedup = StatCard("Ortalama Hızlanma", "—", "Benchmark sonrası", "fa5s.chart-line", "#60a5fa")
        metrics_grid.addWidget(self.card_speedup)

        self.card_critical = StatCard("Kritik Darboğaz", "0", ">400ms sorgular", "fa5s.exclamation-circle", "#93c5fd")
        metrics_grid.addWidget(self.card_critical)

        self.card_safety = StatCard("Güvenlik Durumu", "%100", "ONLINE=ON Korumalı", "fa5s.shield-alt", "#3b82f6")
        metrics_grid.addWidget(self.card_safety)
        self.content_layout.addLayout(metrics_grid)

        # 5. Resizable Splitter between Live Log Stream and Performance Matrix
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setChildrenCollapsible(False)

        # Terminal Card Frame
        terminal_frame = QFrame()
        terminal_frame.setProperty("class", "card-panel")
        term_layout = QVBoxLayout(terminal_frame)
        term_layout.setContentsMargins(12, 8, 12, 8)
        term_layout.setSpacing(6)

        term_topbar = QHBoxLayout()
        term_title = QLabel("CANLI LOG AKIŞI")
        term_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #728499; letter-spacing: 0.5px;")
        term_topbar.addWidget(term_title)
        term_topbar.addStretch()

        self.term_status_lbl = QLabel("HAZIR")
        self.term_status_lbl.setStyleSheet("color: #60a5fa; font-weight: 700; font-size: 9.5px; font-family: 'JetBrains Mono', monospace;")
        term_topbar.addWidget(self.term_status_lbl)

        btn_clear_term = QPushButton("Temizle")
        btn_clear_term.setStyleSheet("font-size: 9.5px; padding: 1px 6px;")
        btn_clear_term.clicked.connect(lambda: self.terminal_box.clear())
        term_topbar.addWidget(btn_clear_term)
        term_layout.addLayout(term_topbar)

        self.terminal_box = QPlainTextEdit()
        self.terminal_box.setReadOnly(True)
        self.terminal_box.setMinimumHeight(100)
        self.terminal_box.setPlaceholderText("[Hazır] SQL Server optimizasyon ve benchmark akışları burada canlı gösterilir...")
        term_layout.addWidget(self.terminal_box)

        main_splitter.addWidget(terminal_frame)

        # 6. Performance Matrix Table Widget (Full-length without inner slider)
        self.matrix_widget = PerformanceMatrixWidget()
        main_splitter.addWidget(self.matrix_widget)

        main_splitter.setSizes([190, 820])
        self.content_layout.addWidget(main_splitter)

        scroll.setWidget(content_widget)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root_layout.addWidget(scroll)

        # Status Bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("VortexDBA Motoru Hazır.")


    def update_header_state(self):
        cfg = get_config()
        db = cfg.database

        # Update DB Capsule text based on current connection status
        if self.is_connected:
            self.btn_db_capsule.setText(f"{db.host}:{db.port} [{db.dbname}]  {self.conn_latency or 0}ms")
            self.btn_db_capsule.setStyleSheet("""
                QPushButton {
                    background: #0c1729;
                    border: 1px solid #1d4ed8;
                    border-radius: 5px;
                    padding: 4px 10px;
                    color: #93c5fd;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 10.5px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #13243f;
                    border-color: #3b82f6;
                    color: #ffffff;
                }
            """)
        else:
            self.btn_db_capsule.setText(f"Çevrimdışı ({db.host}:{db.port}) - Bağlan")
            self.btn_db_capsule.setStyleSheet("""
                QPushButton {
                    background: #140d12;
                    border: 1px solid #4a161f;
                    border-radius: 5px;
                    padding: 4px 10px;
                    color: #fca5a5;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 10.5px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #201118;
                    border-color: #ef4444;
                    color: #ffffff;
                }
            """)

        # Update Mode buttons
        is_auto = (getattr(cfg, "operating_mode", "advisor") == "autonomous")
        self.btn_mode_a.setChecked(not is_auto)
        self.btn_mode_b.setChecked(is_auto)
        self.autopilot_banner.setVisible(is_auto)

        # Update Source buttons
        is_live = (getattr(cfg, "traffic_source", "simulation") == "live_dmv")
        self.btn_src_sim.setChecked(not is_live)
        self.btn_src_live.setChecked(is_live)

    def trigger_connection_check(self, show_connecting: bool = False):
        """Asynchronously verify SQL Server connection without blocking GUI."""
        cfg = get_config()
        db = cfg.database
        if not self.is_connected or show_connecting:
            self.btn_db_capsule.setText(f"Bağlanıyor... [{db.host}:{db.port}]")
            self.btn_db_capsule.setStyleSheet("""
                QPushButton {
                    background: #0d1624;
                    border: 1px solid #2563eb;
                    border-radius: 5px;
                    padding: 4px 10px;
                    color: #60a5fa;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 10.5px;
                    font-weight: 600;
                }
            """)

        if self.check_worker and self.check_worker.isRunning():
            return

        self.check_worker = DbQuickCheckWorker(timeout=2)
        self.check_worker.result_signal.connect(self.on_connection_check_result)
        self.check_worker.start()

    def on_connection_check_result(self, res: dict):
        was_connected = self.is_connected
        self.is_connected = res.get("success", False)
        self.conn_latency = res.get("latency_ms", 0)
        cfg = get_config()
        db = cfg.database

        self.offline_banner.setVisible(not self.is_connected)
        self.update_header_state()

        if self.is_connected:
            if not was_connected:
                self.statusBar().showMessage(f"SQL Server Bağlandı: {db.host}:{db.port} ({self.conn_latency}ms)")
                self.matrix_widget.load_data(is_connected=True)
                self.update_metrics()
        else:
            if was_connected:
                self.statusBar().showMessage("⚠️ SQL Server Bağlantısı Kesildi (Çevrimdışı Mod)")
                self.matrix_widget.load_data(is_connected=False)
                self.update_metrics()
            else:
                self.statusBar().showMessage("SQL Server Bağlantısı Yok (Çevrimdışı Mod)")

    def refresh_all(self):
        self.update_header_state()
        self.matrix_widget.load_data(is_connected=self.is_connected)
        self.update_metrics()
        self.statusBar().showMessage("Paneller güncellendi.")

    def auto_refresh(self):
        # Only monitor connection liveness if currently connected.
        # When offline, do NOT automatically retry connecting in a loop.
        if self.is_connected:
            if not self.current_worker or not self.current_worker.isRunning():
                self.trigger_connection_check(show_connecting=False)


    def update_metrics(self):
        try:
            active_indexes = get_active_indexes()
            idx_count = len(active_indexes)
        except Exception:
            idx_count = 0
        self.card_indexes.set_value(str(idx_count), f"/ 15 Kapsandı")

        matrix = self.matrix_widget.raw_data or []
        multipliers = [m["multiplier"] for m in matrix if isinstance(m, dict) and m.get("multiplier") and m["multiplier"] > 1]
        if multipliers:
            avg_mult = sum(multipliers) / len(multipliers)
            self.card_speedup.set_value(f"{avg_mult:.1f}x", "Daha Hızlı")
        else:
            self.card_speedup.set_value("—", "3. Adım sonrası ölçülür")

        critical = len([m for m in matrix if isinstance(m, dict) and not m.get("has_index") and (m.get("baseline_ms") or 0) > 400])
        self.card_critical.set_value(str(critical), "Kritik darboğaz" if critical > 0 else "Tüm sorgular kabul edilebilir")

    def switch_mode(self, mode: str):
        update_operating_mode(mode)
        self.refresh_all()

    def switch_source(self, source: str):
        update_traffic_source(source)
        self.btn_src_sim.setChecked(source == "simulation")
        self.btn_src_live.setChecked(source == "live_dmv")
        self.refresh_all()

    def open_db_dialog(self):
        dlg = DbConfigDialog(self)
        if dlg.exec():
            self.trigger_connection_check(show_connecting=True)
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
        self.trigger_connection_check()
        self.refresh_all()

    def run_step1(self):
        self.switch_source("simulation")
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
        matrix_data = self.matrix_widget.raw_data or []
        queries = []
        for item in matrix_data:
            sql = item.get("query_sql")
            name = item.get("name") or "query"
            if sql:
                queries.append({"name": name, "query": sql, "params": None})

        self.set_running_state(True)
        self.current_worker = BenchmarkWorker(queries=queries if queries else None)
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
