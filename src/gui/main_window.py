"""Main Application Window for VortexDBA native PyQt6 desktop software.
Refined modern 5-tab architecture with 8-directional border edge resizing.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QStackedWidget,
    QScrollArea,
    QFrame,
    QLabel,
    QPushButton,
    QLineEdit,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QSplitter,
    QCheckBox,
    QSpinBox,
    QGraphicsOpacityEffect,
)

from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QFont, QColor


import qtawesome as qta

try:
    from src.config import get_config, update_database_config, update_operating_mode
    from src.db_connection import (
        get_connection,
        execute_query,
        test_connection,
        is_server_reachable,
    )
    from src.state_store import (
        get_active_indexes,
        get_latest_baseline,
        get_latest_benchmark,
        record_applied_index,
        record_decision,
        record_benchmark,
        record_baseline,
        get_recent_decisions,
        get_captured_queries,
        add_captured_query,
        delete_captured_queries,
        clear_all_captured_queries,
        clear_agent_decisions,
        get_dmv_watermark,
        set_dmv_watermark,
    )
    from src.query_discovery import poll_and_capture_live_dmv_queries, generate_descriptive_title
    from src.index_advisor import recommend_index_for_query
    from src.pg_stats_reader import get_table_stats
    from src.gui.theme import DARK_THEME_QSS, LIGHT_THEME_QSS, get_theme_color
    from src.gui.widgets.stat_card import StatCard
    from src.gui.widgets.toast import ToastOverlay
    from src.gui.widgets.quota_stepper import QuotaStepperWidget
    from src.gui.widgets.theme_toggle import ThemeToggleSwitch
    from src.gui.widgets.fade_overlay import ThemeFadeOverlay
    from src.gui.widgets.lang_toggle import LanguageToggle
    from src.i18n import t, get_language, set_language
    from src.gui.workers import (
        SimulateWorker,
        RemediateWorker,
        BenchmarkWorker,
        ResetWorker,
    )
except ImportError:
    from config import get_config, update_database_config, update_operating_mode
    from db_connection import (
        get_connection,
        execute_query,
        test_connection,
        is_server_reachable,
    )
    from state_store import (
        get_active_indexes,
        get_latest_baseline,
        get_latest_benchmark,
        record_applied_index,
        record_decision,
        record_benchmark,
        record_baseline,
        get_recent_decisions,
        get_captured_queries,
        add_captured_query,
        delete_captured_queries,
        clear_all_captured_queries,
        clear_agent_decisions,
        get_dmv_watermark,
        set_dmv_watermark,
    )

    from query_discovery import poll_and_capture_live_dmv_queries, generate_descriptive_title
    from index_advisor import recommend_index_for_query
    from pg_stats_reader import get_table_stats
    from gui.theme import DARK_THEME_QSS, LIGHT_THEME_QSS, get_theme_color
    from gui.widgets.stat_card import StatCard
    from gui.widgets.toast import ToastOverlay
    from gui.widgets.quota_stepper import QuotaStepperWidget
    from gui.widgets.theme_toggle import ThemeToggleSwitch
    from gui.widgets.fade_overlay import ThemeFadeOverlay
    from gui.widgets.lang_toggle import LanguageToggle
    from i18n import t, get_language, set_language
    from gui.workers import (
        SimulateWorker,
        RemediateWorker,
        BenchmarkWorker,
        ResetWorker,
    )








class MainWindow(QMainWindow):
    """Refined Modern Main Window for VortexDBA native desktop application."""

    BORDER_MARGIN = 8

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VortexDBA - Autonomous SQL Server Engine")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.resize(1440, 920)
        self.setMinimumSize(1100, 720)
        self.setMouseTracking(True)

        self._drag_pos = None
        self._resizing_edge = None
        self._resize_start_pos = None
        self._resize_start_geom = None

        # Load Logo
        logo_path = Path(__file__).resolve().parent.parent.parent / "logo.svg"
        if not logo_path.exists():
            logo_path = Path.cwd() / "logo.svg"
        self.logo_path = logo_path
        if self.logo_path.exists():
            self.setWindowIcon(QIcon(str(self.logo_path)))

        self.current_worker = None
        self.is_connected = False
        self.is_light_theme = False
        cfg = get_config()
        self.engine_active = (getattr(cfg, "operating_mode", "advisor") == "autonomous")  # Synced with config
        self.max_indexes_limit = 5  # Configurable autonomous quota limit
        self.active_editor_rec = None
        self.selected_query_ids = set()
        self.expanded_sql_ids = set()

        # Apply QSS Dark Theme
        self.setStyleSheet(DARK_THEME_QSS)

        self.init_ui()
        self.center_on_screen()
        self.toast_overlay = ToastOverlay(self)
        self.fade_overlay = ThemeFadeOverlay(self)
        self.refresh_all()

        # Auto-refresh timer (3 seconds) for live telemetry & background DMV sniffing
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.auto_refresh)
        self.timer.start(3000)

    def create_expandable_sql_cell(self, q_id: str, full_sql: str, parent_table: QTableWidget, max_collapsed_len: int = 70) -> QWidget:
        """Create a compact SQL cell widget with an interactive expand/collapse arrow toggle."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        is_expanded = q_id in self.expanded_sql_ids

        # Clean single-line summary
        one_line = " ".join(full_sql.split())
        summary_text = one_line if len(one_line) <= max_collapsed_len else one_line[:max_collapsed_len - 3] + "..."

        lbl_sql = QLabel(full_sql if is_expanded else summary_text)
        lbl_sql.setStyleSheet(f"font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 11px; color: {self.c('text_code')};")
        lbl_sql.setWordWrap(is_expanded)
        lbl_sql.setToolTip(full_sql)
        lbl_sql.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        btn_toggle = QPushButton("▼" if is_expanded else "▶")
        btn_toggle.setFixedSize(20, 20)
        btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_toggle.setToolTip("Daralt (Küçült)" if is_expanded else "Genişlet (Büyüt)" if get_language() == "tr" else ("Collapse" if is_expanded else "Expand"))
        btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.c('bg_tertiary')};
                color: {self.c('text_secondary')};
                border: 1px solid {self.c('border_color')};
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {self.c('bg_hover')};
                color: {self.c('accent_primary')};
                border-color: {self.c('accent_primary')};
            }}
        """)

        def _toggle():
            if q_id in self.expanded_sql_ids:
                self.expanded_sql_ids.remove(q_id)
            else:
                self.expanded_sql_ids.add(q_id)

            expanded_now = q_id in self.expanded_sql_ids
            btn_toggle.setText("▼" if expanded_now else "▶")
            btn_toggle.setToolTip("Daralt (Küçült)" if expanded_now else "Genişlet (Büyüt)" if get_language() == "tr" else ("Collapse" if expanded_now else "Expand"))
            lbl_sql.setText(full_sql if expanded_now else summary_text)
            lbl_sql.setWordWrap(expanded_now)
            parent_table.resizeRowsToContents()

        btn_toggle.clicked.connect(_toggle)

        layout.addWidget(btn_toggle, 0, Qt.AlignmentFlag.AlignTop if is_expanded else Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(lbl_sql, 1)

        return widget

    def c(self, key: str) -> str:
        """Returns theme-aware hex color for the active theme."""
        return get_theme_color(self.is_light_theme, key)

    def _update_nav_tabs_visuals(self, active_index: int = None):
        """Visually updates active vs inactive tab buttons with crisp contrast in both themes."""
        if active_index is None:
            active_index = self.stacked_widget.currentIndex() if hasattr(self, "stacked_widget") else 0
        cur_idx = active_index
        tab_buttons = [
            getattr(self, "btn_tab_connect", None),
            getattr(self, "btn_tab_editor", None),
            getattr(self, "btn_tab_queries", None),
            getattr(self, "btn_tab_idx_mgmt", None),
            getattr(self, "btn_tab_mgmt", None),
        ]
        is_light = getattr(self, "is_light_theme", False)

        for i, btn in enumerate(tab_buttons):
            if btn is None:
                continue
            is_active = (i == cur_idx)
            btn.blockSignals(True)
            btn.setChecked(is_active)
            btn.blockSignals(False)

            if is_light:
                if is_active:
                    btn.setStyleSheet("background-color: #0284c7; color: #ffffff; border: none; border-bottom: 3px solid #0369a1; border-right: 1px solid #0369a1; font-weight: 800; font-size: 12px; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; min-width: 105px; max-width: 105px;")
                else:
                    btn.setStyleSheet("background-color: #e2e8f0; color: #334155; border: none; border-right: 1px solid #cbd5e1; font-weight: 700; font-size: 12px; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; min-width: 105px; max-width: 105px;")
            else:
                if is_active:
                    btn.setStyleSheet("background-color: #0e2238; color: #38bdf8; border: none; border-bottom: 3px solid #06b6d4; border-right: 1px solid #1a1a28; font-weight: 800; font-size: 12px; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; min-width: 105px; max-width: 105px;")
                else:
                    btn.setStyleSheet("background-color: #090910; color: #8b8b9e; border: none; border-right: 1px solid #1a1a28; font-weight: 700; font-size: 12px; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; min-width: 105px; max-width: 105px;")

    def _apply_all_button_styles(self):
        """Directly and deterministically applies rich, vibrant color styles to all buttons across the application."""
        is_light = getattr(self, "is_light_theme", False)

        if is_light:
            primary_style = "background-color: #0284c7; color: #ffffff; border: 1px solid #0369a1; font-weight: 800; font-size: 11.5px; border-radius: 3px; padding: 7px 16px; font-family: 'JetBrains Mono', monospace;"
            success_style = "background-color: #059669; color: #ffffff; border: 1px solid #047857; font-weight: 800; font-size: 11.5px; border-radius: 3px; padding: 7px 16px; font-family: 'JetBrains Mono', monospace;"
            warning_style = "background-color: #d97706; color: #ffffff; border: 1px solid #b45309; font-weight: 800; font-size: 11.5px; border-radius: 3px; padding: 7px 16px; font-family: 'JetBrains Mono', monospace;"
            danger_style = "background-color: #e11d48; color: #ffffff; border: 1px solid #be123c; font-weight: 800; font-size: 11.5px; border-radius: 3px; padding: 7px 16px; font-family: 'JetBrains Mono', monospace;"
            secondary_style = "background-color: #e2e8f0; color: #0f172a; border: 1px solid #94a3b8; font-weight: 700; font-size: 11.5px; border-radius: 3px; padding: 7px 14px; font-family: 'JetBrains Mono', monospace;"
            preset_style = "background-color: #f1f5f9; color: #0284c7; border: 1px solid #cbd5e1; font-weight: 700; font-size: 11px; border-radius: 3px; padding: 6px 12px; font-family: 'JetBrains Mono', monospace;"
        else:
            primary_style = "background-color: #1d4ed8; color: #ffffff; border: 1px solid #3b82f6; font-weight: 800; font-size: 11.5px; border-radius: 3px; padding: 7px 16px; font-family: 'JetBrains Mono', monospace;"
            success_style = "background-color: #065f46; color: #ffffff; border: 1px solid #10b981; font-weight: 800; font-size: 11.5px; border-radius: 3px; padding: 7px 16px; font-family: 'JetBrains Mono', monospace;"
            warning_style = "background-color: #854d0e; color: #ffffff; border: 1px solid #f59e0b; font-weight: 800; font-size: 11.5px; border-radius: 3px; padding: 7px 16px; font-family: 'JetBrains Mono', monospace;"
            danger_style = "background-color: #881337; color: #ffffff; border: 1px solid #f43f5e; font-weight: 800; font-size: 11.5px; border-radius: 3px; padding: 7px 16px; font-family: 'JetBrains Mono', monospace;"
            secondary_style = "background-color: #0c0c14; color: #e2e8f0; border: 1px solid #2a2a3c; font-weight: 700; font-size: 11.5px; border-radius: 3px; padding: 7px 14px; font-family: 'JetBrains Mono', monospace;"
            preset_style = "background-color: #05080e; color: #38bdf8; border: 1px solid #1e3a5f; font-weight: 700; font-size: 11px; border-radius: 3px; padding: 6px 12px; font-family: 'JetBrains Mono', monospace;"

        # Primary buttons
        for btn in [getattr(self, "btn_run_sql", None), getattr(self, "btn_refresh_queries", None), getattr(self, "btn_to_editor", None)]:
            if btn: btn.setStyleSheet(primary_style)

        # Success buttons
        for btn in [getattr(self, "btn_save_conn", None), getattr(self, "btn_rem", None), getattr(self, "btn_apply_rec", None)]:
            if btn: btn.setStyleSheet(success_style)

        # Warning buttons
        for btn in [getattr(self, "btn_bench", None)]:
            if btn: btn.setStyleSheet(warning_style)

        # Danger buttons
        for btn in [getattr(self, "btn_reset", None), getattr(self, "btn_delete_selected", None), getattr(self, "btn_clear_all_queries", None)]:
            if btn: btn.setStyleSheet(danger_style)

        # Secondary / Standard buttons
        for btn in [getattr(self, "btn_test_conn", None), getattr(self, "btn_to_queries", None), getattr(self, "btn_clear_sql", None), getattr(self, "btn_select_all_queries", None), getattr(self, "btn_clear_audit", None), getattr(self, "btn_save_mode", None)]:
            if btn: btn.setStyleSheet(secondary_style)

        # Presets & Template buttons
        for btn in getattr(self, "preset_buttons", []):
            btn.setStyleSheet(preset_style)
        for btn in getattr(self, "template_buttons", []):
            btn.setStyleSheet(preset_style)

        # Password toggle button
        btn_pass = getattr(self, "btn_toggle_pass", None)
        if btn_pass:
            if is_light:
                btn_pass.setStyleSheet("QPushButton { background: #e2e8f0; border: 1px solid #cbd5e1; color: #334155; font-size: 13px; font-weight: bold; border-radius: 2px; } QPushButton:hover { background: #cbd5e1; color: #0284c7; border-color: #0284c7; }")
            else:
                btn_pass.setStyleSheet("QPushButton { background: #12121e; border: 1px solid #2e2e42; color: #94a3b8; font-size: 13px; font-weight: bold; border-radius: 2px; } QPushButton:hover { background: #1e1e30; color: #38bdf8; border-color: #38bdf8; }")

    def toggle_password_visibility(self):
        """Toggles SQL Server connection password visibility between masked and plain text."""
        if not hasattr(self, "input_pass") or not hasattr(self, "btn_toggle_pass"):
            return
        if self.input_pass.echoMode() == QLineEdit.EchoMode.Password:
            self.input_pass.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_pass.setText("👁‍🗨")
            self.btn_toggle_pass.setToolTip(t("connect.hide_pass"))
        else:
            self.input_pass.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_pass.setText("👁")
            self.btn_toggle_pass.setToolTip(t("connect.show_pass"))

    def _update_all_labels_theme(self):
        """Dynamically updates contrast and text colors for all panel titles and descriptions."""
        is_light = getattr(self, "is_light_theme", False)
        title_color = "#0f172a" if is_light else "#ffffff"

        for lbl in [
            getattr(self, "lbl_conn_title", None),
            getattr(self, "lbl_server_title", None),
            getattr(self, "lbl_editor_title", None),
            getattr(self, "lbl_queries_title", None),
            getattr(self, "lbl_batch_ops", None),
        ]:
            if lbl:
                lbl.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {title_color}; font-family: 'JetBrains Mono', monospace;")

    def toggle_engine_state(self):
        """Toggles the autonomous indexing engine ON/OFF and updates all UI badges and buttons."""
        self.engine_active = not self.engine_active
        update_operating_mode("autonomous" if self.engine_active else "advisor")
        if self.engine_active:
            self.show_toast(t("toast.engine_active_title"), t("toast.engine_active_msg"), "success")
            if hasattr(self, "term_log"):
                self.term_log.appendPlainText("▶ [ENGINE ACTIVE]: Background DMV query listener & autonomous optimization enabled." if get_language() == "en" else "▶ [MOTOR AKTİF]: Arka plan DMV sorgu dinleyici ve otonom optimizasyon devrede.")
            self.run_autonomous_optimizer_tick()
        else:
            self.show_toast(t("toast.engine_stopped_title"), t("toast.engine_stopped_msg"), "warning")
            if hasattr(self, "term_log"):
                self.term_log.appendPlainText("⏸ [ENGINE STOPPED]: Autonomous listening and automatic indexing paused." if get_language() == "en" else "⏸ [MOTOR DURDURULDU]: Otonom dinleme ve otomatik indeksleme duraklatıldı.")
        self.refresh_engine_ui()

    def refresh_engine_ui(self):
        """Updates autonomous motor status badges and buttons across header and management pages."""
        if hasattr(self, "btn_top_engine"):
            if self.engine_active:
                self.btn_top_engine.setText(t("header.engine_active"))
                self.btn_top_engine.setStyleSheet(
                    f"font-size: 11px; font-weight: 800; font-family: 'JetBrains Mono', monospace; padding: 5px 12px; background: {self.c('badge_engine_on_bg')}; color: {self.c('badge_engine_on_text')}; border: 1px solid {self.c('badge_engine_on_border')}; border-radius: 2px;"
                )
            else:
                self.btn_top_engine.setText(t("header.engine_inactive"))
                self.btn_top_engine.setStyleSheet(
                    f"font-size: 11px; font-weight: 800; font-family: 'JetBrains Mono', monospace; padding: 5px 12px; background: {self.c('badge_engine_off_bg')}; color: {self.c('badge_engine_off_text')}; border: 1px solid {self.c('badge_engine_off_border')}; border-radius: 2px;"
                )
            self.btn_top_engine.setToolTip(t("header.engine_tip"))

        if hasattr(self, "btn_toggle_engine"):
            if self.engine_active:
                self.btn_toggle_engine.setText(t("mgmt.btn_engine_active"))
                self.btn_toggle_engine.setStyleSheet(
                    f"font-size: 11px; font-weight: 800; font-family: 'JetBrains Mono', monospace; padding: 7px 14px; background: {self.c('badge_engine_on_bg')}; color: {self.c('badge_engine_on_text')}; border: 1px solid {self.c('badge_engine_on_border')}; border-radius: 2px;"
                )
            else:
                self.btn_toggle_engine.setText(t("mgmt.btn_engine_inactive"))
                self.btn_toggle_engine.setStyleSheet(
                    f"font-size: 11px; font-weight: 800; font-family: 'JetBrains Mono', monospace; padding: 7px 14px; background: {self.c('badge_engine_off_bg')}; color: {self.c('badge_engine_off_text')}; border: 1px solid {self.c('badge_engine_off_border')}; border-radius: 2px;"
                )

        if hasattr(self, "sc_engine"):
            if self.engine_active:
                self.sc_engine.set_value(t("mgmt.stat_engine_active_val"), t("mgmt.stat_engine_active_sub"))
            else:
                self.sc_engine.set_value(t("mgmt.stat_engine_stopped_val"), t("mgmt.stat_engine_stopped_sub"))


    def switch_page(self, index: int):
        """Switches stacked widget to target page index and synchronizes contiguous navigation buttons."""
        if hasattr(self, "stacked_widget"):
            self.stacked_widget.setCurrentIndex(index)

        # Update visuals of contiguous nav tab buttons
        self._update_nav_tabs_visuals(index)
        self._apply_all_button_styles()
        self._update_all_labels_theme()

        # Refresh the activated page
        if index == 0:
            self.refresh_connect_page()
        elif index == 1:
            if hasattr(self, "sql_editor_input"):
                self.sql_editor_input.setFocus()
        elif index == 2:
            self.load_queries_only_table()
        elif index == 3:
            self.load_index_mgmt_table()
        elif index == 4:
            self.refresh_mgmt_page()

    def set_theme(self, is_light: bool):
        """Smoothly crossfades between Dark and Light theme with 60fps hardware-accelerated snapshot."""
        if hasattr(self, "fade_overlay") and self.isVisible():
            snapshot = self.grab()
            self.fade_overlay.start_crossfade(snapshot, duration_ms=220)

        self.is_light_theme = is_light
        app_inst = QApplication.instance()
        qss = LIGHT_THEME_QSS if is_light else DARK_THEME_QSS
        if app_inst:
            app_inst.setStyleSheet(qss)
        self.setStyleSheet(qss)

        # Update Nav Tabs Box (Seamless contiguous segmented tabs with uniform width)
        if hasattr(self, "nav_tabs_box"):
            if is_light:
                self.nav_tabs_box.setStyleSheet("background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 0px; padding: 0px;")
            else:
                self.nav_tabs_box.setStyleSheet("background: #090910; border: 1px solid #1a1a28; border-radius: 0px; padding: 0px;")

        self._update_nav_tabs_visuals()
        self.refresh_engine_ui()
        self._apply_all_button_styles()
        self._update_all_labels_theme()
        if hasattr(self, "toast_overlay"):
            self.toast_overlay.set_theme(is_light)






        if hasattr(self, "brand_lbl"):
            self.brand_lbl.setStyleSheet(
                f"font-size: 16px; font-weight: 800; color: {self.c('text_primary')}; letter-spacing: 0.8px; font-family: 'JetBrains Mono', monospace;"
            )

        if hasattr(self, "lbl_server_info"):
            self.lbl_server_info.setStyleSheet(
                f"font-size: 11px; font-weight: 700; color: {self.c('text_muted')}; font-family: 'JetBrains Mono', monospace; background: {self.c('bg_subtle')}; border: 1px solid {self.c('border_card')}; padding: 5px 10px; border-radius: 2px;"
            )

        # Update Top Autonomous Engine Badge
        self.refresh_engine_ui()

        # Update Health Box
        if hasattr(self, "lbl_health_box"):
            cfg = get_config()
            if self.is_connected:
                self.lbl_health_box.setText(f"ONLINE | :{cfg.database.port}")
                self.lbl_health_box.setStyleSheet(
                    f"font-size: 11px; font-weight: 800; font-family: 'JetBrains Mono', monospace; padding: 5px 12px; background: {self.c('badge_online_bg')}; color: {self.c('badge_online_text')}; border: 1px solid {self.c('badge_online_border')}; border-radius: 2px;"
                )
            else:
                self.lbl_health_box.setText(t("header.health_offline"))
                self.lbl_health_box.setStyleSheet(
                    f"font-size: 11px; font-weight: 800; font-family: 'JetBrains Mono', monospace; padding: 5px 12px; background: {self.c('badge_offline_bg')}; color: {self.c('badge_offline_text')}; border: 1px solid {self.c('badge_offline_border')}; border-radius: 2px;"
                )


        # Update Execution Stats Strip
        if hasattr(self, "lbl_exec_stats"):
            self.lbl_exec_stats.setStyleSheet(
                f"background: {self.c('strip_bg')}; border: 1px solid {self.c('strip_border')}; padding: 6px 12px; font-size: 11px; font-weight: 700; color: {self.c('strip_text')}; font-family: 'JetBrains Mono', monospace;"
            )

        # Update Dynamic Index Recommendation Banner
        if hasattr(self, "rec_frame"):
            self.rec_frame.setStyleSheet(
                f"background: {self.c('rec_bg')}; border: 1px solid {self.c('rec_border')}; padding: 8px;"
            )
        if hasattr(self, "lbl_rec_text"):
            self.lbl_rec_text.setStyleSheet(
                f"color: {self.c('rec_text')}; font-size: 11px; font-family: 'JetBrains Mono', monospace;"
            )

        # Update Connection Diagnostic Label
        if hasattr(self, "lbl_test_diag"):
            self.lbl_test_diag.setStyleSheet(
                f"background: {self.c('bg_subtle')}; border: 1px solid {self.c('border_card')}; padding: 10px; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: {self.c('text_primary')};"
            )

        # Update Last Action Label
        if hasattr(self, "lbl_last_action"):
            self.lbl_last_action.setStyleSheet(
                f"color: {self.c('text_primary')}; font-weight: 700; font-size: 11px; font-family: 'JetBrains Mono', monospace;"
            )

        # Update Windows Control buttons
        if hasattr(self, "btn_min") and hasattr(self, "btn_max") and hasattr(self, "btn_close"):
            win_color = "#334155" if is_light else "#cbd5e1"
            hover_bg = "#e2e8f0" if is_light else "#151522"
            hover_border = "#cbd5e1" if is_light else "#2e2e42"
            win_style = f"""
                QPushButton {{
                    background: transparent;
                    border: 1px solid transparent;
                    color: {win_color};
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 13px;
                    font-weight: 700;
                    padding: 0;
                }}
                QPushButton:hover {{
                    background: {hover_bg};
                    border: 1px solid {hover_border};
                    color: {"#0f172a" if is_light else "#ffffff"};
                }}
            """
            self.btn_min.setStyleSheet(win_style)
            self.btn_max.setStyleSheet(win_style)

        # Update Quota Stepper Widgets
        if hasattr(self, "spin_quota_mgmt"):
            self.spin_quota_mgmt.apply_theme(is_light)

        # Update StatCards
        for sc in self.findChildren(StatCard):
            sc.apply_theme(is_light)

        if hasattr(self, "lang_toggle"):
            self.lang_toggle.set_theme(is_light)

        # Reload only the currently active page for instant, freeze-free response
        cur_idx = self.stacked_widget.currentIndex() if hasattr(self, "stacked_widget") else 0
        if cur_idx == 0:
            self.refresh_connect_page()
        elif cur_idx == 2:
            self.load_queries_only_table()
        elif cur_idx == 3:
            self.load_index_mgmt_table()
        elif cur_idx == 4:
            self.refresh_mgmt_page()

    def on_language_changed(self, lang: str):
        """Called when user switches language between EN and TR."""
        set_language(lang)
        self.retranslate_ui()

    def retranslate_ui(self):
        """Dynamically translates all static and dynamic UI elements into the active language."""
        # Top Nav Tabs
        if hasattr(self, "btn_tab_connect"): self.btn_tab_connect.setText(t("nav.server"))
        if hasattr(self, "btn_tab_editor"): self.btn_tab_editor.setText(t("nav.sql"))
        if hasattr(self, "btn_tab_queries"): self.btn_tab_queries.setText(t("nav.queries"))
        if hasattr(self, "btn_tab_idx_mgmt"): self.btn_tab_idx_mgmt.setText(t("nav.index"))
        if hasattr(self, "btn_tab_mgmt"): self.btn_tab_mgmt.setText(t("nav.management"))

        # Header controls
        if hasattr(self, "btn_min"): self.btn_min.setToolTip(t("header.win_min"))
        if hasattr(self, "btn_max"): self.btn_max.setToolTip(t("header.win_max"))
        if hasattr(self, "btn_close"): self.btn_close.setToolTip(t("header.win_close"))
        if hasattr(self, "theme_switch"): self.theme_switch.setToolTip(t("header.theme_tip"))
        if hasattr(self, "lang_toggle"): self.lang_toggle.setToolTip(t("header.lang_tip"))

        # Connect Page
        if hasattr(self, "lbl_conn_title"): self.lbl_conn_title.setText(t("connect.target_conn_title"))
        if hasattr(self, "lbl_conn_desc"): self.lbl_conn_desc.setText(t("connect.target_conn_desc"))
        if hasattr(self, "lbl_form_host"): self.lbl_form_host.setText(t("connect.host"))
        if hasattr(self, "lbl_form_port"): self.lbl_form_port.setText(t("connect.port"))
        if hasattr(self, "lbl_form_dbname"): self.lbl_form_dbname.setText(t("connect.dbname"))
        if hasattr(self, "lbl_form_user"): self.lbl_form_user.setText(t("connect.user"))
        if hasattr(self, "lbl_form_pass"): self.lbl_form_pass.setText(t("connect.pass"))
        if hasattr(self, "lbl_presets_head"): self.lbl_presets_head.setText(t("connect.quick_presets"))
        if hasattr(self, "btn_p1"): self.btn_p1.setText(t("connect.preset_docker"))
        if hasattr(self, "btn_p2"): self.btn_p2.setText(t("connect.preset_master"))
        if hasattr(self, "btn_test_conn"): self.btn_test_conn.setText(t("connect.btn_test"))
        if hasattr(self, "btn_save_conn"): self.btn_save_conn.setText(t("connect.btn_save"))
        if hasattr(self, "lbl_server_title"): self.lbl_server_title.setText(t("connect.live_server_title"))
        if hasattr(self, "lbl_tbls_head"): self.lbl_tbls_head.setText(t("connect.tables_section"))
        if hasattr(self, "table_db_stats"):
            self.table_db_stats.setHorizontalHeaderLabels([t("connect.tbl_col_name"), t("connect.tbl_col_rows"), t("connect.tbl_col_scan"), t("connect.tbl_col_seek")])
        if hasattr(self, "btn_to_editor"): self.btn_to_editor.setText(t("connect.btn_to_editor"))
        if hasattr(self, "btn_to_queries"): self.btn_to_queries.setText(t("connect.btn_to_queries"))

        # Editor Page
        if hasattr(self, "lbl_editor_title"): self.lbl_editor_title.setText(t("editor.title"))
        if hasattr(self, "btn_clear_sql"): self.btn_clear_sql.setText(t("editor.btn_clear"))
        if hasattr(self, "btn_run_sql"): self.btn_run_sql.setText(t("editor.btn_run"))
        if hasattr(self, "lbl_sample_queries"): self.lbl_sample_queries.setText(t("editor.sample_queries"))
        if hasattr(self, "btn_s1"): self.btn_s1.setText(t("editor.sample_p1"))
        if hasattr(self, "btn_s2"): self.btn_s2.setText(t("editor.sample_p2"))
        if hasattr(self, "btn_s3"): self.btn_s3.setText(t("editor.sample_p3"))
        if hasattr(self, "btn_s4"): self.btn_s4.setText(t("editor.sample_p4"))
        if hasattr(self, "btn_apply_editor_rec"): self.btn_apply_editor_rec.setText(t("editor.rec_btn"))
        if hasattr(self, "lbl_results_head"): self.lbl_results_head.setText("QUERY RESULTS (DATA GRID):" if get_language() == "en" else "SORGU SONUÇLARI (DATA GRID):")

        # Queries Page
        if hasattr(self, "lbl_queries_title"): self.lbl_queries_title.setText(t("queries.title"))
        if hasattr(self, "btn_refresh_queries"): self.btn_refresh_queries.setText(t("queries.btn_refresh"))
        if hasattr(self, "btn_select_all_queries"): self.btn_select_all_queries.setText(t("queries.btn_select_all"))
        if hasattr(self, "btn_delete_selected"): self.btn_delete_selected.setText(t("queries.btn_delete_selected"))
        if hasattr(self, "btn_clear_all_queries"): self.btn_clear_all_queries.setText(t("queries.btn_clear_all"))
        if hasattr(self, "table_queries_only"):
            self.table_queries_only.setHorizontalHeaderLabels([
                t("queries.col_select"),
                t("queries.col_title"),
                t("queries.col_sql"),
                t("queries.col_status"),
                t("queries.col_time"),
                t("queries.col_dur")
            ])

        # Index Management Page
        if hasattr(self, "lbl_batch_ops"): self.lbl_batch_ops.setText(t("index.batch_ops"))
        if hasattr(self, "btn_rem"): self.btn_rem.setText(t("index.btn_apply_all"))
        if hasattr(self, "btn_bench"): self.btn_bench.setText(t("index.btn_benchmark_all"))
        if hasattr(self, "btn_reset"): self.btn_reset.setText(t("index.btn_reset"))
        if hasattr(self, "lbl_idx_table1_title"): self.lbl_idx_table1_title.setText(t("index.table1_title"))
        if hasattr(self, "table_idx_mgmt"):
            self.table_idx_mgmt.setHorizontalHeaderLabels([
                t("index.t1_col_query"),
                t("index.t1_col_sql"),
                t("index.t1_col_match"),
                t("index.t1_col_before"),
                t("index.t1_col_after"),
                t("index.t1_col_speedup"),
                t("index.t1_col_actions")
            ])
        if hasattr(self, "lbl_idx_table2_title"): self.lbl_idx_table2_title.setText(t("index.table2_title"))
        if hasattr(self, "table_idx_catalog"):
            self.table_idx_catalog.setHorizontalHeaderLabels([
                t("index.t2_col_no"),
                t("index.t2_col_name"),
                t("index.t2_col_status"),
                t("index.t2_col_ddl"),
                t("index.t2_col_queries"),
                t("index.t2_col_actions")
            ])

        # Connect Page Password Toggle Tooltip
        if hasattr(self, "btn_toggle_pass") and hasattr(self, "input_pass"):
            self.btn_toggle_pass.setToolTip(t("connect.hide_pass") if self.input_pass.echoMode() == QLineEdit.EchoMode.Normal else t("connect.show_pass"))

        # Management Page
        if hasattr(self, "lbl_mgmt_engine_ctrl"): self.lbl_mgmt_engine_ctrl.setText(t("mgmt.engine_ctrl_title"))
        if hasattr(self, "lbl_mgmt_last_action_title"): self.lbl_mgmt_last_action_title.setText(t("mgmt.last_action_title"))
        if hasattr(self, "lbl_mgmt_quota_title"): self.lbl_mgmt_quota_title.setText(t("mgmt.quota_title"))
        if hasattr(self, "lbl_mgmt_quota_label"): self.lbl_mgmt_quota_label.setText(t("mgmt.quota_label"))
        if hasattr(self, "lbl_mgmt_safety_strip"): self.lbl_mgmt_safety_strip.setText(t("mgmt.safety_strip"))
        if hasattr(self, "lbl_mgmt_audit_title"): self.lbl_mgmt_audit_title.setText(t("mgmt.audit_title"))
        if hasattr(self, "btn_clear_audit"): self.btn_clear_audit.setText(t("mgmt.btn_clear_audit"))
        if hasattr(self, "table_decisions"):
            self.table_decisions.setHorizontalHeaderLabels([t("mgmt.audit_col_type"), t("mgmt.audit_col_details"), t("mgmt.audit_col_time")])
        if hasattr(self, "lbl_mgmt_telemetry_title"): self.lbl_mgmt_telemetry_title.setText(t("mgmt.telemetry_title"))

        # Health Box
        if hasattr(self, "lbl_health_box"):
            cfg = get_config()
            if self.is_connected:
                self.lbl_health_box.setText(f"ONLINE | :{cfg.database.port}")
            else:
                self.lbl_health_box.setText(t("header.health_offline"))

        self.refresh_engine_ui()
        self.refresh_connect_page()
        self.load_queries_only_table()
        self.load_index_mgmt_table()
        self.refresh_mgmt_page()







    def center_on_screen(self):
        """Center the window perfectly on the primary screen available geometry."""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(max(geo.x(), x), max(geo.y(), y))

    def show_toast(self, title: str, message: str, toast_type: str = "success"):
        """Displays a sleek floating non-blocking persistent toast notification."""
        if hasattr(self, "toast_overlay"):
            self.toast_overlay.add_toast(title, message, toast_type, is_light=getattr(self, "is_light_theme", False))


    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "toast_overlay"):
            self.toast_overlay.reposition()
        if hasattr(self, "fade_overlay"):
            self.fade_overlay.resize(self.size())


    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.btn_max.setText("□")
        else:
            self.showMaximized()
            self.btn_max.setText("❐")
        if hasattr(self, "toast_overlay"):
            self.toast_overlay.reposition()


    # -------------------------------------------------------------------------
    # 8-DIRECTIONAL BORDER RESIZING & TITLE BAR DRAGGING
    # -------------------------------------------------------------------------
    BORDER_MARGIN = 10

    def _get_resize_edge(self, pos: QPoint, rect: QRect) -> str | None:
        if self.isMaximized():
            return None

        x, y = pos.x(), pos.y()
        w, h = rect.width(), rect.height()
        m = self.BORDER_MARGIN

        left = x <= m
        right = x >= w - m
        top = y <= m
        bottom = y >= h - m

        if top and left:
            return "top_left"
        if top and right:
            return "top_right"
        if bottom and left:
            return "bottom_left"
        if bottom and right:
            return "bottom_right"
        if left:
            return "left"
        if right:
            return "right"
        if top:
            return "top"
        if bottom:
            return "bottom"
        return None

    def _update_resize_cursor(self, edge: str | None):
        if self.isMaximized() or edge is None:
            self.unsetCursor()
            return
        if edge in ("top_left", "bottom_right"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge in ("top_right", "bottom_left"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif edge in ("left", "right"):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge in ("top", "bottom"):
            self.setCursor(Qt.CursorShape.SizeVerCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            pos = event.position().toPoint()
            rect = self.rect()
            edge = self._get_resize_edge(pos, rect)
            if edge is not None:
                self._resizing_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geom = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        rect = self.rect()

        if getattr(self, "_resizing_edge", None) is not None:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            start_g = self._resize_start_geom
            min_w = self.minimumWidth()
            min_h = self.minimumHeight()

            new_x = start_g.x()
            new_y = start_g.y()
            new_w = start_g.width()
            new_h = start_g.height()

            edge = self._resizing_edge
            if "left" in edge:
                calc_w = start_g.width() - delta.x()
                if calc_w >= min_w:
                    new_x = start_g.x() + delta.x()
                    new_w = calc_w
                else:
                    new_x = start_g.x() + (start_g.width() - min_w)
                    new_w = min_w
            elif "right" in edge:
                new_w = max(min_w, start_g.width() + delta.x())

            if "top" in edge:
                calc_h = start_g.height() - delta.y()
                if calc_h >= min_h:
                    new_y = start_g.y() + delta.y()
                    new_h = calc_h
                else:
                    new_y = start_g.y() + (start_g.height() - min_h)
                    new_h = min_h
            elif "bottom" in edge:
                new_h = max(min_h, start_g.height() + delta.y())

            self.setGeometry(new_x, new_y, new_w, new_h)
            event.accept()
            return

        if not self.isMaximized():
            edge = self._get_resize_edge(pos, rect)
            self._update_resize_cursor(edge)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._resizing_edge = None
        self.unsetCursor()
        super().mouseReleaseEvent(event)

    def eventFilter(self, obj, event):
        if not self.isMaximized():
            if event.type() in (event.Type.HoverMove, event.Type.MouseMove):
                g_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else None
                if g_pos:
                    pos = self.mapFromGlobal(g_pos)
                    rect = self.rect()
                    edge = self._get_resize_edge(pos, rect)
                    if getattr(self, "_resizing_edge", None) is not None:
                        self.mouseMoveEvent(event)
                        return True
                    self._update_resize_cursor(edge)

            elif event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    g_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else None
                    if g_pos:
                        pos = self.mapFromGlobal(g_pos)
                        rect = self.rect()
                        edge = self._get_resize_edge(pos, rect)
                        if edge is not None:
                            self._resizing_edge = edge
                            self._resize_start_pos = g_pos
                            self._resize_start_geom = self.geometry()
                            return True

            elif event.type() == event.Type.MouseButtonRelease:
                if getattr(self, "_resizing_edge", None) is not None:
                    self._resizing_edge = None
                    self.unsetCursor()
                    return True

        if obj == getattr(self, "header_frame", None):
            pos = event.position().toPoint() if hasattr(event, "position") else QPoint(0, 0)
            rect = self.rect()

            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    edge = self._get_resize_edge(pos, rect)
                    if edge is not None and not self.isMaximized():
                        self._resizing_edge = edge
                        self._resize_start_pos = event.globalPosition().toPoint()
                        self._resize_start_geom = self.geometry()
                        return True
                    self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    return False
            elif event.type() == event.Type.MouseMove:
                if getattr(self, "_resizing_edge", None) is not None:
                    self.mouseMoveEvent(event)
                    return True
                if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
                    if self.isMaximized():
                        self.showNormal()
                        self.btn_max.setText("□")
                    self.move(event.globalPosition().toPoint() - self._drag_pos)
                    return True
                edge = self._get_resize_edge(pos, rect)
                self._update_resize_cursor(edge)
            elif event.type() == event.Type.MouseButtonRelease:
                self._drag_pos = None
                self._resizing_edge = None
                self.unsetCursor()
            elif event.type() == event.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.toggle_maximize()
                    return True
        return super().eventFilter(obj, event)


    # -------------------------------------------------------------------------
    # UI SETUP
    # -------------------------------------------------------------------------
    def init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")
        central_widget.setMouseTracking(True)
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. TOP HEADER & MODERN NAV-BAR
        self.header_frame = QFrame()
        self.header_frame.setProperty("class", "header-panel")
        self.header_frame.setFixedHeight(50)
        self.header_frame.setMouseTracking(True)
        self.header_frame.installEventFilter(self)

        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(14, 0, 8, 0)
        header_layout.setSpacing(10)

        # Brand Logo & Title (Enlarged, no version text)
        brand_box = QHBoxLayout()
        brand_box.setSpacing(10)
        logo_lbl = QLabel()
        if self.logo_path.exists():
            logo_pix = QIcon(str(self.logo_path)).pixmap(24, 24)
            logo_lbl.setPixmap(logo_pix)
        else:
            try:
                logo_lbl.setPixmap(qta.icon("fa5s.bolt", color="#06b6d4").pixmap(22, 22))
            except Exception:
                pass
        brand_box.addWidget(logo_lbl)

        self.brand_lbl = QLabel("VORTEX DBA")
        self.brand_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff; letter-spacing: 0.8px; font-family: 'JetBrains Mono', monospace;")
        brand_box.addWidget(self.brand_lbl)
        header_layout.addLayout(brand_box)

        header_layout.addSpacing(6)

        # 5 Tab Navigation Buttons (Contiguous Segmented Bar)
        self.nav_tabs_box = QFrame()
        self.nav_tabs_box.setStyleSheet("background: #090910; border: 1px solid #1a1a28; border-radius: 0px; padding: 0px;")
        nav_tabs_layout = QHBoxLayout(self.nav_tabs_box)
        nav_tabs_layout.setContentsMargins(0, 0, 0, 0)
        nav_tabs_layout.setSpacing(0)


        self.btn_tab_connect = QPushButton("SUNUCU")
        self.btn_tab_connect.setProperty("class", "nav-tab-btn")
        self.btn_tab_connect.setFixedWidth(105)
        self.btn_tab_connect.setCheckable(True)
        self.btn_tab_connect.setChecked(True)
        self.btn_tab_connect.clicked.connect(lambda: self.switch_page(0))
        nav_tabs_layout.addWidget(self.btn_tab_connect)

        self.btn_tab_editor = QPushButton("SQL")
        self.btn_tab_editor.setProperty("class", "nav-tab-btn")
        self.btn_tab_editor.setFixedWidth(105)
        self.btn_tab_editor.setCheckable(True)
        self.btn_tab_editor.clicked.connect(lambda: self.switch_page(1))
        nav_tabs_layout.addWidget(self.btn_tab_editor)

        self.btn_tab_queries = QPushButton("SORGULAR")
        self.btn_tab_queries.setProperty("class", "nav-tab-btn")
        self.btn_tab_queries.setFixedWidth(105)
        self.btn_tab_queries.setCheckable(True)
        self.btn_tab_queries.clicked.connect(lambda: self.switch_page(2))
        nav_tabs_layout.addWidget(self.btn_tab_queries)

        self.btn_tab_idx_mgmt = QPushButton("İNDEKS")
        self.btn_tab_idx_mgmt.setProperty("class", "nav-tab-btn")
        self.btn_tab_idx_mgmt.setFixedWidth(105)
        self.btn_tab_idx_mgmt.setCheckable(True)
        self.btn_tab_idx_mgmt.clicked.connect(lambda: self.switch_page(3))
        nav_tabs_layout.addWidget(self.btn_tab_idx_mgmt)

        self.btn_tab_mgmt = QPushButton("YÖNETİM")
        self.btn_tab_mgmt.setProperty("class", "nav-tab-btn")
        self.btn_tab_mgmt.setFixedWidth(105)
        self.btn_tab_mgmt.setCheckable(True)
        self.btn_tab_mgmt.clicked.connect(lambda: self.switch_page(4))
        nav_tabs_layout.addWidget(self.btn_tab_mgmt)



        header_layout.addWidget(self.nav_tabs_box)
        header_layout.addStretch()

        # Right Side Server Info & Status
        self.lbl_server_info = QLabel("localhost:1433 / vortex_db")
        self.lbl_server_info.setStyleSheet("font-size: 11px; font-weight: 700; color: #9494a8; font-family: 'JetBrains Mono', monospace; background: #050508; border: 1px solid #1a1a24; padding: 5px 10px;")
        header_layout.addWidget(self.lbl_server_info)

        # Top Autonomous Engine Status Badge (Live & Clickable)
        self.btn_top_engine = QPushButton("● OTONOM: AKTİF (7/24)")
        self.btn_top_engine.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_top_engine.setToolTip("Otonom İndeksleme Motorunu Aç/Kapat (Tıkla)")
        self.btn_top_engine.setStyleSheet("font-size: 11px; font-weight: 800; font-family: 'JetBrains Mono', monospace; padding: 5px 12px; background: #041a12; color: #10b981; border: 1px solid #10b981; border-radius: 2px;")
        self.btn_top_engine.clicked.connect(self.toggle_engine_state)
        header_layout.addWidget(self.btn_top_engine)

        # Health Box (Green when connected, Red when disconnected)
        self.lbl_health_box = QLabel("OFFLINE")
        self.lbl_health_box.setStyleSheet("font-size: 11px; font-weight: 800; font-family: 'JetBrains Mono', monospace; padding: 5px 12px; background: #1f060c; color: #f43f5e; border: 1px solid #f43f5e;")
        header_layout.addWidget(self.lbl_health_box)

        # Dark / Light Animated Theme Toggle Switch (from Uiverse.io Madflows)
        self.theme_switch = ThemeToggleSwitch(is_light=False)
        self.theme_switch.toggled.connect(self.set_theme)
        header_layout.addWidget(self.theme_switch)

        # Segmented Language Selector [ EN | TR ]
        self.lang_toggle = LanguageToggle(current_lang=get_language(), is_light=False)
        self.lang_toggle.language_changed.connect(self.on_language_changed)
        header_layout.addWidget(self.lang_toggle)


        # Crisp Windows Controls
        win_controls = QHBoxLayout()
        win_controls.setSpacing(2)
        win_controls.setContentsMargins(4, 0, 0, 0)

        btn_win_style = """
            QPushButton {
                background: transparent;
                border: 1px solid transparent;
                color: #cbd5e1;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                font-weight: 700;
                padding: 0;
            }
            QPushButton:hover {
                background: #151522;
                border: 1px solid #2e2e42;
                color: #ffffff;
            }
        """

        self.btn_min = QPushButton("—")
        self.btn_min.setFixedSize(34, 28)
        self.btn_min.setStyleSheet(btn_win_style)
        self.btn_min.setToolTip("Simge Durumuna Küçült")
        self.btn_min.clicked.connect(self.showMinimized)
        win_controls.addWidget(self.btn_min)

        self.btn_max = QPushButton("□")
        self.btn_max.setFixedSize(34, 28)
        self.btn_max.setStyleSheet(btn_win_style)
        self.btn_max.setToolTip("Ekranı Kapla / Geri Yükle")
        self.btn_max.clicked.connect(self.toggle_maximize)
        win_controls.addWidget(self.btn_max)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(34, 28)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid transparent;
                color: #cbd5e1;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                font-weight: 700;
                padding: 0;
            }
            QPushButton:hover {
                background: #e11d48;
                border: 1px solid #f43f5e;
                color: #ffffff;
            }
        """)
        self.btn_close.setToolTip("Kapat")
        self.btn_close.clicked.connect(self.close)
        win_controls.addWidget(self.btn_close)

        header_layout.addLayout(win_controls)
        root_layout.addWidget(self.header_frame)

        # 2. STACKED WIDGET FOR 5 PAGES
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: transparent;")


        # Create 5 Pages
        self.page_connect = self.create_connect_page()
        self.page_editor = self.create_editor_page()
        self.page_queries = self.create_queries_page()
        self.page_idx_mgmt = self.create_index_mgmt_page()
        self.page_mgmt = self.create_mgmt_page()

        self.stacked_widget.addWidget(self.page_connect)   # Index 0
        self.stacked_widget.addWidget(self.page_editor)    # Index 1
        self.stacked_widget.addWidget(self.page_queries)   # Index 2
        self.stacked_widget.addWidget(self.page_idx_mgmt)  # Index 3
        self.stacked_widget.addWidget(self.page_mgmt)      # Index 4


        root_layout.addWidget(self.stacked_widget, 1)
        self._apply_hand_cursor_recursively(self)
        self._update_nav_tabs_visuals()
        self.refresh_engine_ui()
        self._apply_all_button_styles()
        self._update_all_labels_theme()
        self.retranslate_ui()






    def _apply_hand_cursor_recursively(self, widget: QWidget):
        from PyQt6.QtWidgets import QAbstractButton, QComboBox
        for btn in widget.findChildren(QAbstractButton):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        for cb in widget.findChildren(QComboBox):
            cb.setCursor(Qt.CursorShape.PointingHandCursor)

    # -------------------------------------------------------------------------
    # PAGE 0: SUNUCU BAĞLANTISI (Server Login)
    # -------------------------------------------------------------------------

    def create_connect_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(16)

        cfg = get_config()

        # Left Card: Connection Parameters Form
        left_card = QFrame()
        left_card.setProperty("class", "card-panel")
        l_layout = QVBoxLayout(left_card)
        l_layout.setContentsMargins(18, 18, 18, 18)
        l_layout.setSpacing(12)

        self.lbl_conn_title = QLabel(t("connect.target_conn_title"))
        self.lbl_conn_title.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {self.c('text_primary')}; font-family: 'JetBrains Mono', monospace;")
        l_layout.addWidget(self.lbl_conn_title)

        self.lbl_conn_desc = QLabel(t("connect.target_conn_desc"))
        self.lbl_conn_desc.setStyleSheet(f"color: {self.c('text_muted')}; font-size: 11px;")
        self.lbl_conn_desc.setWordWrap(True)
        l_layout.addWidget(self.lbl_conn_desc)

        grid = QGridLayout()
        grid.setSpacing(10)

        self.lbl_form_host = QLabel(t("connect.host"))
        grid.addWidget(self.lbl_form_host, 0, 0)
        self.input_host = QLineEdit(cfg.database.host)
        grid.addWidget(self.input_host, 0, 1)

        self.lbl_form_port = QLabel(t("connect.port"))
        grid.addWidget(self.lbl_form_port, 0, 2)
        self.input_port = QLineEdit(str(cfg.database.port))
        grid.addWidget(self.input_port, 0, 3)

        self.lbl_form_dbname = QLabel(t("connect.dbname"))
        grid.addWidget(self.lbl_form_dbname, 1, 0)
        self.input_dbname = QLineEdit(cfg.database.dbname)
        grid.addWidget(self.input_dbname, 1, 1, 1, 3)

        self.lbl_form_user = QLabel(t("connect.user"))
        grid.addWidget(self.lbl_form_user, 2, 0)
        self.input_user = QLineEdit(cfg.database.user)
        grid.addWidget(self.input_user, 2, 1)

        self.lbl_form_pass = QLabel(t("connect.pass"))
        grid.addWidget(self.lbl_form_pass, 2, 2)

        pass_row = QHBoxLayout()
        pass_row.setSpacing(4)
        pass_row.setContentsMargins(0, 0, 0, 0)
        self.input_pass = QLineEdit(cfg.database.password)
        self.input_pass.setEchoMode(QLineEdit.EchoMode.Password)
        pass_row.addWidget(self.input_pass, 1)

        self.btn_toggle_pass = QPushButton("👁")
        self.btn_toggle_pass.setFixedSize(32, 28)
        self.btn_toggle_pass.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_pass.setToolTip(t("connect.show_pass"))
        self.btn_toggle_pass.clicked.connect(self.toggle_password_visibility)
        pass_row.addWidget(self.btn_toggle_pass)
        grid.addLayout(pass_row, 2, 3)

        l_layout.addLayout(grid)


        # Quick Presets
        self.lbl_presets_head = QLabel(t("connect.quick_presets"))
        l_layout.addWidget(self.lbl_presets_head)
        preset_box = QHBoxLayout()
        self.btn_p1 = QPushButton(t("connect.preset_docker"))
        self.btn_p1.clicked.connect(lambda: self.set_preset("localhost", 1433, "vortex_db", "sa", "VortexPassword123!"))
        preset_box.addWidget(self.btn_p1)

        self.btn_p2 = QPushButton(t("connect.preset_master"))
        self.btn_p2.clicked.connect(lambda: self.set_preset("127.0.0.1", 1433, "master", "sa", "VortexPassword123!"))
        preset_box.addWidget(self.btn_p2)
        l_layout.addLayout(preset_box)
        self.preset_buttons = [self.btn_p1, self.btn_p2]


        # Action Buttons
        btn_box = QHBoxLayout()
        self.btn_test_conn = QPushButton(t("connect.btn_test"))
        self.btn_test_conn.clicked.connect(self.on_test_connection)
        btn_box.addWidget(self.btn_test_conn)

        self.btn_save_conn = QPushButton(t("connect.btn_save"))
        self.btn_save_conn.setProperty("class", "btn-success")
        self.btn_save_conn.clicked.connect(self.on_save_connection)
        btn_box.addWidget(self.btn_save_conn)
        l_layout.addLayout(btn_box)

        # Diagnostic Box
        self.lbl_test_diag = QLabel()
        self.lbl_test_diag.setStyleSheet("background: #020204; border: 1px solid #1a1a24; padding: 10px; font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        self.lbl_test_diag.setVisible(False)
        self.lbl_test_diag.setWordWrap(True)
        l_layout.addWidget(self.lbl_test_diag)

        l_layout.addStretch()
        layout.addWidget(left_card, 1)

        # Right Card: Live Server & Tables Overview
        right_card = QFrame()
        right_card.setProperty("class", "card-panel")
        r_layout = QVBoxLayout(right_card)
        r_layout.setContentsMargins(18, 18, 18, 18)
        r_layout.setSpacing(12)

        self.lbl_server_title = QLabel(t("connect.live_server_title"))
        self.lbl_server_title.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {self.c('text_primary')}; font-family: 'JetBrains Mono', monospace;")
        r_layout.addWidget(self.lbl_server_title)

        self.lbl_conn_state = QLabel(t("connect.state_checking"))
        self.lbl_conn_state.setStyleSheet("color: #06b6d4; font-size: 11.5px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        r_layout.addWidget(self.lbl_conn_state)

        self.lbl_tbls_head = QLabel(t("connect.tables_section"))
        r_layout.addWidget(self.lbl_tbls_head)

        self.table_db_stats = QTableWidget()
        self.table_db_stats.setColumnCount(4)
        self.table_db_stats.setHorizontalHeaderLabels([t("connect.tbl_col_name"), t("connect.tbl_col_rows"), t("connect.tbl_col_scan"), t("connect.tbl_col_seek")])
        self.table_db_stats.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_db_stats.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_db_stats.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_db_stats.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        r_layout.addWidget(self.table_db_stats, 1)

        nav_btns = QHBoxLayout()
        self.btn_to_editor = QPushButton(t("connect.btn_to_editor"))
        self.btn_to_editor.setProperty("class", "btn-primary")
        self.btn_to_editor.clicked.connect(lambda: self.switch_page(1))
        nav_btns.addWidget(self.btn_to_editor)

        self.btn_to_queries = QPushButton(t("connect.btn_to_queries"))
        self.btn_to_queries.clicked.connect(lambda: self.switch_page(2))
        nav_btns.addWidget(self.btn_to_queries)
        r_layout.addLayout(nav_btns)



        layout.addWidget(right_card, 1)
        return page

    def set_preset(self, host, port, dbname, user, password):
        self.input_host.setText(host)
        self.input_port.setText(str(port))
        self.input_dbname.setText(dbname)
        self.input_user.setText(user)
        self.input_pass.setText(password)

    def on_test_connection(self):
        host = self.input_host.text().strip()
        port = int(self.input_port.text().strip() or 1433)
        dbname = self.input_dbname.text().strip()
        user = self.input_user.text().strip()
        password = self.input_pass.text()

        self.lbl_test_diag.setVisible(True)
        self.lbl_test_diag.setText("Sunucuya bağlanılıyor...")
        self.lbl_test_diag.setStyleSheet("background: #0d0d14; border: 1px solid #1a1a24; color: #06b6d4; padding: 10px;")

        res = test_connection(host, port, dbname, user, password)
        if res.get("success"):
            self.lbl_test_diag.setStyleSheet("background: #041a12; border: 1px solid #10b981; color: #6ee7b7; padding: 10px;")
            self.lbl_test_diag.setText(f"BAĞLANTI BAŞARILI!\n{res.get('server_version', 'Microsoft SQL Server')}\nHedef DB: [{res.get('database')}]")
        else:
            self.lbl_test_diag.setStyleSheet("background: #1f060c; border: 1px solid #f43f5e; color: #fca5a5; padding: 10px;")
            self.lbl_test_diag.setText(f"BAĞLANTI HATASI:\n{res.get('error')}")

    def on_save_connection(self):
        host = self.input_host.text().strip()
        port = int(self.input_port.text().strip() or 1433)
        dbname = self.input_dbname.text().strip()
        user = self.input_user.text().strip()
        password = self.input_pass.text()

        res = test_connection(host, port, dbname, user, password)
        if not res.get("success"):
            QMessageBox.warning(self, "Bağlantı Hatası", f"Sunucuya bağlanılamadı:\n{res.get('error')}")
            return

        update_database_config(host, port, dbname, user, password)
        self.lbl_test_diag.setVisible(True)
        self.lbl_test_diag.setStyleSheet("background: #041a12; border: 1px solid #10b981; color: #6ee7b7; padding: 10px;")
        self.lbl_test_diag.setText("Bağlantı parametreleri başarıyla kaydedildi ve aktif edildi!")

        self.refresh_all()

    def refresh_connect_page(self):
        cfg = get_config()
        self.lbl_server_info.setText(f"{cfg.database.host}:{cfg.database.port} / {cfg.database.dbname}")

        if not self.is_connected:
            self.lbl_conn_state.setText("SQL Server Bağlantısı Yok (Sunucu Kapalı veya Port Ulaşılamaz)")
            self.lbl_conn_state.setStyleSheet("color: #f43f5e; font-weight: 700;")
            self.table_db_stats.setRowCount(0)
            return

        self.lbl_conn_state.setText(f"Bağlantı Aktif: {cfg.database.host}:{cfg.database.port} / {cfg.database.dbname}")
        self.lbl_conn_state.setStyleSheet("color: #10b981; font-weight: 700;")

        try:
            stats = get_table_stats()
            self.table_db_stats.setRowCount(len(stats))
            for i, st in enumerate(stats):
                item_name = QTableWidgetItem(st.relname)
                item_name.setForeground(QColor(self.c("text_primary")))

                item_rows = QTableWidgetItem(f"{st.n_live_tup:,}")
                item_rows.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item_rows.setForeground(QColor(self.c("text_secondary")))

                item_seq = QTableWidgetItem(f"{st.seq_scan:,}")
                item_seq.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if st.seq_scan > 0:
                    item_seq.setForeground(QColor(self.c("accent_danger")))
                else:
                    item_seq.setForeground(QColor(self.c("text_muted")))

                item_idx = QTableWidgetItem(f"{st.idx_scan:,}")
                item_idx.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item_idx.setForeground(QColor(self.c("accent_success")))

                self.table_db_stats.setItem(i, 0, item_name)
                self.table_db_stats.setItem(i, 1, item_rows)
                self.table_db_stats.setItem(i, 2, item_seq)
                self.table_db_stats.setItem(i, 3, item_idx)

        except Exception:
            pass

    # -------------------------------------------------------------------------
    # PAGE 1: SQL EDİTÖRÜ (Interactive SQL Runner)
    # -------------------------------------------------------------------------
    def create_editor_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card-panel")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(10)

        # Top Toolbar
        top_bar = QHBoxLayout()
        self.lbl_editor_title = QLabel(t("editor.title"))
        self.lbl_editor_title.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {self.c('text_primary')}; font-family: 'JetBrains Mono', monospace;")
        top_bar.addWidget(self.lbl_editor_title)
        top_bar.addStretch()


        self.btn_clear_sql = QPushButton(t("editor.btn_clear"))
        self.btn_clear_sql.clicked.connect(self.clear_sql_editor)
        top_bar.addWidget(self.btn_clear_sql)

        self.btn_run_sql = QPushButton(t("editor.btn_run"))
        self.btn_run_sql.setProperty("class", "btn-primary")
        self.btn_run_sql.clicked.connect(self.execute_user_sql)
        top_bar.addWidget(self.btn_run_sql)
        c_layout.addLayout(top_bar)

        # Quick Sample Queries
        samples_box = QHBoxLayout()
        samples_box.setSpacing(6)
        self.lbl_sample_queries = QLabel(t("editor.sample_queries"))
        self.lbl_sample_queries.setStyleSheet("font-size: 10.5px; color: #9494a8; font-weight: 700;")
        samples_box.addWidget(self.lbl_sample_queries)

        self.btn_s1 = QPushButton(t("editor.sample_p1"))
        self.btn_s1.clicked.connect(lambda: self.set_editor_query("SELECT status, COUNT(*) AS siparis_sayisi, SUM(total_amount) AS toplam_ciro FROM orders WHERE status = 'completed' GROUP BY status;"))
        samples_box.addWidget(self.btn_s1)

        self.btn_s2 = QPushButton(t("editor.sample_p2"))
        self.btn_s2.clicked.connect(lambda: self.set_editor_query("SELECT TOP 50 id, customer_id, order_date, total_amount, status FROM orders WHERE status = 'completed' ORDER BY order_date DESC;"))
        samples_box.addWidget(self.btn_s2)

        self.btn_s3 = QPushButton(t("editor.sample_p3"))
        self.btn_s3.clicked.connect(lambda: self.set_editor_query("SELECT c.city, COUNT(o.id) AS order_count, SUM(o.total_amount) AS total_spent FROM customers c JOIN orders o ON c.id = o.customer_id WHERE o.status = 'completed' GROUP BY c.city;"))
        samples_box.addWidget(self.btn_s3)

        self.btn_s4 = QPushButton(t("editor.sample_p4"))
        self.btn_s4.clicked.connect(lambda: self.set_editor_query("SELECT id, first_name, last_name, email, city FROM customers WHERE email LIKE '%@gmail.com' AND city = 'Istanbul';"))
        samples_box.addWidget(self.btn_s4)

        samples_box.addStretch()
        c_layout.addLayout(samples_box)
        self.template_buttons = [self.btn_s1, self.btn_s2, self.btn_s3, self.btn_s4]


        # Code Input Editor
        self.sql_editor_input = QPlainTextEdit()
        self.sql_editor_input.setFixedHeight(150)
        self.sql_editor_input.setPlainText("SELECT status, COUNT(*) AS siparis_sayisi, SUM(total_amount) AS toplam_ciro FROM orders WHERE status = 'completed' GROUP BY status;")
        c_layout.addWidget(self.sql_editor_input)


        # Execution Stats Strip
        self.lbl_exec_stats = QLabel("EXECUTION TIME: - ms   |   RETURNED ROWS: -   |   COLUMNS: -" if get_language() == "en" else "YÜRÜTME SÜRESİ: - ms   |   DÖNEN SATIR: -   |   SÜTUN SAYISI: -")
        self.lbl_exec_stats.setStyleSheet("background: #040407; border: 1px solid #1a1a24; padding: 6px 12px; font-size: 11px; font-weight: 700; color: #cbd5e1; font-family: 'JetBrains Mono', monospace;")
        c_layout.addWidget(self.lbl_exec_stats)

        # Index Recommendation Banner (Hidden by default)
        self.rec_frame = QFrame()
        self.rec_frame.setStyleSheet("background: #03141c; border: 1px solid #06b6d4; padding: 8px;")
        self.rec_frame.setVisible(False)
        rec_layout = QHBoxLayout(self.rec_frame)
        rec_layout.setContentsMargins(10, 6, 10, 6)

        self.lbl_rec_text = QLabel()
        self.lbl_rec_text.setStyleSheet("color: #6ee7b7; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        self.lbl_rec_text.setWordWrap(True)
        rec_layout.addWidget(self.lbl_rec_text, 1)

        self.btn_apply_editor_rec = QPushButton(t("editor.rec_btn"))
        self.btn_apply_editor_rec.setProperty("class", "btn-success")
        self.btn_apply_editor_rec.clicked.connect(self.apply_editor_rec)
        rec_layout.addWidget(self.btn_apply_editor_rec)
        c_layout.addWidget(self.rec_frame)

        # Result Data Table
        self.lbl_results_head = QLabel("QUERY RESULTS (DATA GRID):" if get_language() == "en" else "SORGU SONUÇLARI (DATA GRID):")
        c_layout.addWidget(self.lbl_results_head)

        self.table_sql_results = QTableWidget()
        c_layout.addWidget(self.table_sql_results, 1)

        layout.addWidget(card)
        return page

    def set_editor_query(self, sql: str):
        self.sql_editor_input.setPlainText(sql)
        self.execute_user_sql()

    def clear_sql_editor(self):
        self.sql_editor_input.clear()
        self.table_sql_results.setRowCount(0)
        self.table_sql_results.setColumnCount(0)
        self.rec_frame.setVisible(False)
        self.lbl_exec_stats.setText("YÜRÜTME SÜRESİ: - ms   |   DÖNEN SATIR: -   |   SÜTUN SAYISI: -")

    def execute_user_sql(self):
        query = self.sql_editor_input.toPlainText().strip()
        if not query:
            return

        t0 = time.perf_counter()
        try:
            conn = get_connection(autocommit=True)
            try:
                with conn.cursor(as_dict=True) as cur:
                    cur.execute(query)
                    t1 = time.perf_counter()
                    elapsed_ms = round((t1 - t0) * 1000.0, 2)

                    rows = []
                    cols = []
                    if cur.description:
                        cols = [d[0] for d in cur.description]
                        rows = cur.fetchmany(500)

                    self.lbl_exec_stats.setText(f"YÜRÜTME SÜRESİ: {elapsed_ms} ms   |   DÖNEN SATIR: {len(rows)}   |   SÜTUN SAYISI: {len(cols)}")
                    self.lbl_exec_stats.setStyleSheet(f"background: {self.c('strip_bg')}; border: 1px solid {self.c('strip_border')}; padding: 6px 12px; font-size: 11px; font-weight: 700; color: {self.c('strip_text')}; font-family: 'JetBrains Mono', monospace;")

                    self.table_sql_results.setColumnCount(len(cols))
                    self.table_sql_results.setRowCount(len(rows))
                    self.table_sql_results.setHorizontalHeaderLabels(cols)

                    for r_idx, row in enumerate(rows):
                        for c_idx, col in enumerate(cols):
                            val = row.get(col)
                            txt = str(val) if val is not None else "NULL"
                            item = QTableWidgetItem(txt)
                            if val is None:
                                item.setForeground(QColor(self.c("text_dim")))
                            else:
                                item.setForeground(QColor(self.c("text_primary")))
                            self.table_sql_results.setItem(r_idx, c_idx, item)

                    # Persist user query to captured_queries list
                    target_tbl = "orders" if "orders" in query.lower() else ("customers" if "customers" in query.lower() else "user_table")
                    q_count = len(get_captured_queries()) + 1
                    
                    # Check if matching custom index was active at moment of execution
                    applied_idx_name = ""
                    try:
                        active_idx = get_active_indexes()
                        rec_check = recommend_index_for_query(query)
                        target_cols = set(rec_check.columns) if rec_check else set()
                        for idx in active_idx:
                            if idx.table_name == target_tbl:
                                if not target_cols or target_cols.issubset(set(idx.columns)) or set(idx.columns).issubset(target_cols):
                                    applied_idx_name = idx.index_name
                                    break
                        if not applied_idx_name:
                            # Check SQL Server sys.indexes directly
                            with conn.cursor(as_dict=True) as cur_check:
                                cur_check.execute("""
                                    SELECT i.name AS index_name, STRING_AGG(c.name, ', ') AS cols
                                    FROM sys.indexes i
                                    JOIN sys.tables t ON t.object_id = i.object_id
                                    JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
                                    JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
                                    WHERE t.name = %s AND i.is_primary_key = 0 AND i.is_unique_constraint = 0 AND i.name NOT IN ('idx_orders_customer_id', 'idx_customers_email')
                                    GROUP BY i.name
                                """, (target_tbl,))
                                for dbi in (cur_check.fetchall() or []):
                                    db_cols = set(c.strip() for c in dbi["cols"].split(",")) if dbi.get("cols") else set()
                                    if not target_cols or target_cols.issubset(db_cols) or target_cols.intersection(db_cols):
                                        applied_idx_name = dbi["index_name"]
                                        break
                    except Exception:
                        pass

                    import uuid
                    title = generate_descriptive_title(query, target_tbl, q_count)
                    if applied_idx_name:
                        title += " (İndeksli Test)"

                    q_name = f"editor_q_{q_count:02d}_{uuid.uuid4().hex[:6]}"
                    add_captured_query(title, query, target_tbl, elapsed_ms, query_name=q_name, applied_index=applied_idx_name)
                    if applied_idx_name:
                        record_benchmark(q_name, elapsed_ms, elapsed_ms, "editor_indexed")
                    else:
                        record_baseline(q_name, elapsed_ms)

                    # Sync with DMV tracker using actual execution stats from SQL Server
                    try:
                        with conn.cursor(as_dict=True) as cur_s:
                            cur_s.execute("""
                                SELECT TOP 1 qs.execution_count AS calls, CONVERT(VARCHAR(19), qs.last_execution_time, 120) AS last_exec 
                                FROM sys.dm_exec_query_stats qs 
                                CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st 
                                WHERE st.text LIKE ?
                                ORDER BY qs.last_execution_time DESC
                            """, (f"%{query[:35]}%",))
                            s_row = cur_s.fetchone()
                            if s_row:
                                import hashlib
                                q_hash = hashlib.md5(" ".join(query.lower().split()).encode("utf-8")).hexdigest()
                                from state_store import update_dmv_tracker
                                update_dmv_tracker(q_hash, int(s_row.get("calls") or 1), str(s_row.get("last_exec") or ""))
                    except Exception:
                        pass

                    # Sync all pages
                    self.load_queries_only_table()
                    self.load_index_mgmt_table()
                    self.refresh_mgmt_page()

                    # Dynamic Index Recommendation check
                    rec = recommend_index_for_query(query)
                    if rec and rec.create_statement:
                        self.active_editor_rec = rec
                        self.active_editor_rec_query = query
                        self.rec_frame.setVisible(True)
                        self.rec_frame.setStyleSheet(f"background: {self.c('rec_bg')}; border: 1px solid {self.c('rec_border')}; padding: 8px;")
                        self.lbl_rec_text.setStyleSheet(f"color: {self.c('rec_text')}; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
                        self.lbl_rec_text.setText(f"DİNAMİK İNDEKS ÖNERİSİ (IndexAdvisor):\n{rec.create_statement}")
                    else:
                        self.rec_frame.setVisible(False)
                        self.active_editor_rec = None

            finally:
                conn.close()
        except Exception as e:
            t1 = time.perf_counter()
            elapsed_ms = round((t1 - t0) * 1000.0, 2)
            self.lbl_exec_stats.setText(f"HATA ({elapsed_ms} ms): {e}")
            self.lbl_exec_stats.setStyleSheet(f"background: {self.c('strip_bg')}; border: 1px solid {self.c('accent_danger')}; padding: 6px 12px; font-size: 11px; font-weight: 700; color: {self.c('accent_danger')}; font-family: 'JetBrains Mono', monospace;")
            self.rec_frame.setVisible(False)
            QMessageBox.critical(self, "SQL Hatası", str(e))

            QMessageBox.critical(self, "SQL Hatası", str(e))

    def apply_editor_rec(self):
        if not self.active_editor_rec:
            return

        rec = self.active_editor_rec
        try:
            conn = get_connection(autocommit=True)
            try:
                with conn.cursor() as cur:
                    cur.execute(rec.create_statement)
            finally:
                conn.close()

            record_applied_index(rec.index_name, rec.table, rec.columns, rec.create_statement, "SQL Editörü isteği")
            record_decision("applied_index", f"Oluşturuldu: [{rec.index_name}] ON [{rec.table}]")
            self.show_toast("İNDEKS OLUŞTURULDU", f"[{rec.index_name}] indeksi SQL Server üzerinde başarıyla oluşturuldu!", "success")
            self.rec_frame.setVisible(False)
            self.load_queries_only_table()
            self.load_index_mgmt_table()
            self.refresh_mgmt_page()
        except Exception as e:
            self.show_toast("İNDEKS HATASI", str(e), "danger")


    # -------------------------------------------------------------------------
    # PAGE 2: SORGULAR (Clean Query List with Refresh, Select & Delete)
    # -------------------------------------------------------------------------
    def create_queries_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card-panel")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(10)

        # Header Toolbar with Refresh, Select & Delete Actions
        top_bar = QHBoxLayout()
        self.lbl_queries_title = QLabel(t("queries.title"))
        self.lbl_queries_title.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {self.c('text_primary')}; font-family: 'JetBrains Mono', monospace;")
        top_bar.addWidget(self.lbl_queries_title)
        top_bar.addStretch()


        self.btn_refresh_queries = QPushButton(t("queries.btn_refresh"))
        self.btn_refresh_queries.setProperty("class", "btn-primary")
        self.btn_refresh_queries.clicked.connect(self.manual_refresh_queries)
        top_bar.addWidget(self.btn_refresh_queries)

        self.btn_select_all_queries = QPushButton(t("queries.btn_select_all"))
        self.btn_select_all_queries.clicked.connect(self.toggle_select_all_queries)
        top_bar.addWidget(self.btn_select_all_queries)

        self.btn_delete_selected = QPushButton(t("queries.btn_delete_selected"))
        self.btn_delete_selected.setProperty("class", "btn-danger")
        self.btn_delete_selected.clicked.connect(self.delete_selected_queries)
        top_bar.addWidget(self.btn_delete_selected)

        self.btn_clear_all_queries = QPushButton(t("queries.btn_clear_all"))
        self.btn_clear_all_queries.setProperty("class", "btn-danger")
        self.btn_clear_all_queries.clicked.connect(self.clear_all_queries_prompt)
        top_bar.addWidget(self.btn_clear_all_queries)

        c_layout.addLayout(top_bar)

        # Table of Queries Only
        self.table_queries_only = QTableWidget()
        self.table_queries_only.setColumnCount(6)
        self.table_queries_only.setHorizontalHeaderLabels([
            t("queries.col_select"),
            t("queries.col_title"),
            t("queries.col_sql"),
            t("queries.col_status"),
            t("queries.col_time"),
            t("queries.col_dur")
        ])
        self.table_queries_only.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_queries_only.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_queries_only.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_queries_only.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_queries_only.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_queries_only.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        c_layout.addWidget(self.table_queries_only, 1)

        layout.addWidget(card)
        return page

    def manual_refresh_queries(self):
        if self.is_connected:
            try:
                new_qs = poll_and_capture_live_dmv_queries()
                if new_qs:
                    self.term_log.appendPlainText(f"⚡ [MANUEL YENİLE]: {len(new_qs)} yeni DMV sorgusu yakalandı." if get_language() == "tr" else f"⚡ [MANUAL REFRESH]: {len(new_qs)} new DMV queries captured.")
            except Exception:
                pass
        self.load_queries_only_table()
        self.load_index_mgmt_table()
        self.refresh_mgmt_page()

    def load_queries_only_table(self):
        # Fetch active custom indexes in SQL Server
        DEFAULT_SCHEMA_INDEXES = {"idx_orders_customer_id", "idx_customers_email"}
        q_idx = """
            SELECT 
                t.name AS table_name,
                i.name AS index_name,
                STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns
            FROM sys.indexes i
            JOIN sys.tables t ON t.object_id = i.object_id
            JOIN sys.index_columns ic ON ic.object_id = ic.object_id AND ic.index_id = i.index_id
            JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
            WHERE t.is_ms_shipped = 0 AND i.name IS NOT NULL 
              AND i.is_primary_key = 0 AND i.is_unique_constraint = 0 AND ic.is_included_column = 0
            GROUP BY t.name, i.name
        """
        active_custom_indexes = []
        if self.is_connected:
            try:
                rows = execute_query(q_idx) or []
                for r in rows:
                    if r["index_name"] not in DEFAULT_SCHEMA_INDEXES:
                        active_custom_indexes.append(r)
            except Exception:
                pass

        applied_db_records = {idx.index_name: idx for idx in get_active_indexes()}

        # Load persisted queries
        persisted = get_captured_queries()
        self.table_queries_only.setRowCount(len(persisted))

        for row_idx, q in enumerate(persisted):
            q_id = q["id"]
            query_sql = q["query_sql"].strip()
            target_tbl = q.get("target_table", "orders")

            # 0. Checkbox
            chk = QCheckBox()
            chk.setChecked(q_id in self.selected_query_ids)
            chk.stateChanged.connect(lambda state, qid=q_id: self.on_query_check_changed(qid, state))
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.addWidget(chk)
            cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            self.table_queries_only.setCellWidget(row_idx, 0, cell_widget)

            # 1. Title & Table
            t_str = f"{q.get('title', 'Sorgu')}\nTablo: [{target_tbl}]" if get_language() == "tr" else f"{q.get('title', 'Query')}\nTable: [{target_tbl}]"
            it_1 = QTableWidgetItem(t_str)
            it_1.setForeground(QColor(self.c("text_primary")))
            self.table_queries_only.setItem(row_idx, 1, it_1)

            # 2. SQL (Expandable / Collapsible)
            sql_cell = self.create_expandable_sql_cell(f"qonly_{q_id}", query_sql, self.table_queries_only, max_collapsed_len=85)
            self.table_queries_only.setCellWidget(row_idx, 2, sql_cell)

            # 3. Index Status (Preserves execution time snapshot - NEVER changes retroactively)
            applied_idx = q.get("applied_index", "")
            if applied_idx:
                live = applied_db_records.get(applied_idx)
                ddl = live.create_sql if live else f"CREATE NONCLUSTERED INDEX [{applied_idx}] ON [{target_tbl}] ...;"
                cols_str = ", ".join(live.columns) if live else "Kolon Bilgisi"
                tooltip_text = (
                    f"APPLIED INDEX DETAILS:\n"
                    f"----------------------------------------\n"
                    f"• Index Name : [{applied_idx}]\n"
                    f"• Target Table: {target_tbl}\n"
                    f"• Columns    : ({cols_str})\n"
                    f"• Status     : Active on SQL Server (Online)\n"
                    f"• DDL Query  :\n{ddl}"
                ) if get_language() == "en" else (
                    f"UYGULANAN İNDEKS DETAYI:\n"
                    f"----------------------------------------\n"
                    f"• İndeks Adı : [{applied_idx}]\n"
                    f"• Hedef Tablo: {target_tbl}\n"
                    f"• Kolonlar   : ({cols_str})\n"
                    f"• Durum      : SQL Server Üzerinde Aktif (Online)\n"
                    f"• DDL Tanımı :\n{ddl}"
                )

                it_idx = QTableWidgetItem(t("queries.status_applied"))
                it_idx.setForeground(QColor(self.c("accent_success")))
                it_idx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_idx.setToolTip(tooltip_text)
            else:
                rec = recommend_index_for_query(query_sql)
                rec_hint = (f"\n\nRecommended Index: {rec.index_name} ON ({', '.join(rec.columns)})" if get_language() == "en" else f"\n\nÖnerilen İndeks: {rec.index_name} ON ({', '.join(rec.columns)})") if rec else ""
                it_idx = QTableWidgetItem(t("queries.status_no_index"))
                it_idx.setForeground(QColor(self.c("text_muted")))
                it_idx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_idx.setToolTip(f"This query was executed without an index.{rec_hint}" if get_language() == "en" else f"Bu sorgu çalıştırıldığı sırada indekssiz olarak yürütülmüştür.{rec_hint}")
            
            self.table_queries_only.setItem(row_idx, 3, it_idx)

            # 4. Timestamp
            it_4 = QTableWidgetItem(q.get("created_at", "-"))
            it_4.setForeground(QColor(self.c("accent_cyan")))
            it_4.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_queries_only.setItem(row_idx, 4, it_4)

            # 5. Duration (Pure white in dark theme, pure black in light theme)
            ms_val = q.get("initial_ms")
            ms_str = f"{ms_val} ms" if ms_val is not None else "—"
            it_5 = QTableWidgetItem(ms_str)
            it_5.setForeground(QColor("#000000" if self.is_light_theme else "#ffffff"))
            it_5.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_queries_only.setItem(row_idx, 5, it_5)

        self.table_queries_only.resizeRowsToContents()

    def on_query_check_changed(self, q_id: int, state: int):
        if state == Qt.CheckState.Checked.value:
            self.selected_query_ids.add(q_id)
        else:
            self.selected_query_ids.discard(q_id)

    def toggle_select_all_queries(self):
        persisted = get_captured_queries()
        if not persisted:
            return

        all_ids = {q["id"] for q in persisted}
        if self.selected_query_ids == all_ids:
            self.selected_query_ids.clear()
        else:
            self.selected_query_ids = all_ids.copy()

        self.load_queries_only_table()

    def delete_selected_queries(self):
        if not self.selected_query_ids:
            self.show_toast(t("toast.no_select_title"), t("toast.no_select_msg"), "warning")
            return

        cnt = len(self.selected_query_ids)
        delete_captured_queries(list(self.selected_query_ids))
        self.selected_query_ids.clear()
        self.load_queries_only_table()
        self.load_index_mgmt_table()
        self.refresh_mgmt_page()
        self.show_toast(t("toast.queries_deleted_title"), t("toast.queries_deleted_msg", cnt=cnt), "danger")

    def clear_all_queries_prompt(self):
        ret = QMessageBox.question(self, t("queries.btn_clear_all"), "Tüm yakalanan ve çalıştırılan sorgu kayıtları silinecektir. Onaylıyor musunuz?" if get_language() == "tr" else "All captured and executed query records will be deleted. Are you sure?")
        if ret == QMessageBox.StandardButton.Yes:
            clear_all_captured_queries()
            self.selected_query_ids.clear()
            self.load_queries_only_table()
            self.load_index_mgmt_table()
            self.refresh_mgmt_page()
            self.show_toast(t("toast.all_cleared_title"), t("toast.all_cleared_msg"), "info")


    # -------------------------------------------------------------------------
    # PAGE 3: İNDEKS YÖNETİMİ (Index Recommendations, DDL, Benchmarks, Apply All)
    # -------------------------------------------------------------------------
    def create_index_mgmt_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)

        # Batch Operations Toolbar
        tb_card = QFrame()
        tb_card.setProperty("class", "card-panel")
        tb_layout = QHBoxLayout(tb_card)
        tb_layout.setContentsMargins(14, 10, 14, 10)
        tb_layout.setSpacing(10)

        self.lbl_batch_ops = QLabel(t("index.batch_ops"))
        self.lbl_batch_ops.setStyleSheet(f"font-size: 11.5px; font-weight: 800; color: {self.c('text_primary')}; font-family: 'JetBrains Mono', monospace;")
        tb_layout.addWidget(self.lbl_batch_ops)
        tb_layout.addStretch()

        self.btn_rem = QPushButton(t("index.btn_apply_all"))
        self.btn_rem.setProperty("class", "btn-success")
        self.btn_rem.clicked.connect(self.run_remediate_worker)
        tb_layout.addWidget(self.btn_rem)

        self.btn_bench = QPushButton(t("index.btn_benchmark_all"))
        self.btn_bench.setProperty("class", "btn-warning")
        self.btn_bench.clicked.connect(self.run_benchmark_worker)
        tb_layout.addWidget(self.btn_bench)

        self.btn_reset = QPushButton(t("index.btn_reset"))
        self.btn_reset.setProperty("class", "btn-danger")
        self.btn_reset.clicked.connect(self.run_reset_worker)
        tb_layout.addWidget(self.btn_reset)

        layout.addWidget(tb_card)

        # Index Management & Recommendation Matrix
        # 1. Query - Index Mapping Table
        card1 = QFrame()
        card1.setProperty("class", "card-panel")
        c1_layout = QVBoxLayout(card1)
        c1_layout.setContentsMargins(14, 14, 14, 14)
        c1_layout.setSpacing(8)

        self.lbl_idx_table1_title = QLabel(t("index.table1_title"))
        self.lbl_idx_table1_title.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {self.c('text_primary')}; font-family: 'JetBrains Mono', monospace;")
        c1_layout.addWidget(self.lbl_idx_table1_title)

        self.table_idx_mgmt = QTableWidget()
        self.table_idx_mgmt.setColumnCount(7)
        self.table_idx_mgmt.setHorizontalHeaderLabels([
            t("index.t1_col_query"),
            t("index.t1_col_sql"),
            t("index.t1_col_match"),
            t("index.t1_col_before"),
            t("index.t1_col_after"),
            t("index.t1_col_speedup"),
            t("index.t1_col_actions")
        ])
        self.table_idx_mgmt.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_idx_mgmt.horizontalHeader().setStretchLastSection(False)
        self.table_idx_mgmt.setColumnWidth(0, 180)
        self.table_idx_mgmt.setColumnWidth(1, 280)
        self.table_idx_mgmt.setColumnWidth(2, 140)
        self.table_idx_mgmt.setColumnWidth(3, 110)
        self.table_idx_mgmt.setColumnWidth(4, 110)
        self.table_idx_mgmt.setColumnWidth(5, 110)
        self.table_idx_mgmt.setColumnWidth(6, 130)
        c1_layout.addWidget(self.table_idx_mgmt)
        layout.addWidget(card1, 3)

        # 2. Numbered Index Catalog & Details Table
        card2 = QFrame()
        card2.setProperty("class", "card-panel")
        c2_layout = QVBoxLayout(card2)
        c2_layout.setContentsMargins(14, 14, 14, 14)
        c2_layout.setSpacing(8)

        self.lbl_idx_table2_title = QLabel(t("index.table2_title"))
        self.lbl_idx_table2_title.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {self.c('text_primary')}; font-family: 'JetBrains Mono', monospace;")
        c2_layout.addWidget(self.lbl_idx_table2_title)

        self.table_idx_catalog = QTableWidget()
        self.table_idx_catalog.setColumnCount(6)
        self.table_idx_catalog.setHorizontalHeaderLabels([
            t("index.t2_col_no"),
            t("index.t2_col_name"),
            t("index.t2_col_status"),
            t("index.t2_col_ddl"),
            t("index.t2_col_queries"),
            t("index.t2_col_actions")
        ])
        self.table_idx_catalog.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_idx_catalog.horizontalHeader().setStretchLastSection(False)
        self.table_idx_catalog.setColumnWidth(0, 90)
        self.table_idx_catalog.setColumnWidth(1, 180)
        self.table_idx_catalog.setColumnWidth(2, 120)
        self.table_idx_catalog.setColumnWidth(3, 280)
        self.table_idx_catalog.setColumnWidth(4, 210)
        self.table_idx_catalog.setColumnWidth(5, 130)
        c2_layout.addWidget(self.table_idx_catalog)
        layout.addWidget(card2, 2)


        return page

    def load_index_mgmt_table(self):
        # Fetch active custom indexes in SQL Server
        DEFAULT_SCHEMA_INDEXES = {"idx_orders_customer_id", "idx_customers_email"}
        q_idx = """
            SELECT 
                SCHEMA_NAME(t.schema_id) AS schema_name,
                t.name AS table_name,
                i.name AS index_name,
                STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns
            FROM sys.indexes i
            JOIN sys.tables t ON t.object_id = i.object_id
            JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
            JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
            WHERE t.is_ms_shipped = 0 AND i.name IS NOT NULL 
              AND i.is_primary_key = 0 AND i.is_unique_constraint = 0 AND ic.is_included_column = 0
            GROUP BY SCHEMA_NAME(t.schema_id), t.name, i.name
        """
        all_active_rows = execute_query(q_idx) or [] if self.is_connected else []
        active_custom_rows = [r for r in all_active_rows if r["index_name"] not in DEFAULT_SCHEMA_INDEXES]

        active_by_table = {}
        for r in active_custom_rows:
            tbl = r["table_name"]
            sch = r.get("schema_name", "dbo")
            cols = [c.strip() for c in r["columns"].split(",")] if r["columns"] else []
            entry = {"name": r["index_name"], "columns": set(cols), "cols_str": r["columns"]}
            for k in [tbl, f"{sch}.{tbl}", tbl.lower(), f"{sch}.{tbl}".lower()]:
                if k not in active_by_table:
                    active_by_table[k] = []
                if entry not in active_by_table[k]:
                    active_by_table[k].append(entry)

        # Load persisted queries
        persisted = get_captured_queries()
        queries_to_display = []

        for p in persisted:
            queries_to_display.append({
                "id": p.get("query_name", f"q_{p['id']}"),
                "title": p.get("title", "Özel Sorgu"),
                "query_sql": p["query_sql"].strip(),
                "target_table": p.get("target_table", "orders"),
                "initial_ms": p.get("initial_ms", 50.0),
                "applied_index": p.get("applied_index", ""),
            })

        # ---------------------------------------------------------------------
        # BUILD UNIFIED NUMBERED INDEX CATALOG
        # ---------------------------------------------------------------------
        unique_indexes = {}
        query_matched_idx_key = {}

        for item in queries_to_display:
            q_id = item["id"]
            q_title = item["title"]
            query_sql = item["query_sql"]
            target_table = item["target_table"]

            rec = recommend_index_for_query(query_sql)
            target_cols = set(rec.columns) if rec else set()
            recommended_sql = rec.create_statement if rec else f"CREATE NONCLUSTERED INDEX [idx_{target_table}_custom] ON [{target_table}] (status) WITH (ONLINE = ON);"
            recommended_name = rec.index_name if rec else f"idx_{target_table}_custom"
            cols_str = ", ".join(rec.columns) if rec else "status"

            matching_live = []
            if target_table in active_by_table:
                for live_idx in active_by_table[target_table]:
                    if target_cols and (target_cols.issubset(live_idx["columns"]) or live_idx["columns"].issubset(target_cols)):
                        matching_live.append(live_idx["name"])

            idx_name = matching_live[0] if matching_live else recommended_name
            is_active = len(matching_live) > 0
            idx_key = (target_table, idx_name)

            if idx_key not in unique_indexes:
                idx_num = f"İndeks #{len(unique_indexes) + 1:02d}"
                unique_indexes[idx_key] = {
                    "num": idx_num,
                    "name": idx_name,
                    "table": target_table,
                    "columns": cols_str,
                    "ddl": recommended_sql,
                    "is_active": is_active,
                    "matching_live": matching_live,
                    "queries": []
                }
            if q_title not in unique_indexes[idx_key]["queries"]:
                unique_indexes[idx_key]["queries"].append(q_title)
            query_matched_idx_key[q_id] = idx_key

        # Also add any active custom indexes on SQL Server not yet mapped
        for r in active_custom_rows:
            tbl = r["table_name"]
            nm = r["index_name"]
            k = (tbl, nm)
            if k not in unique_indexes:
                idx_num = f"İndeks #{len(unique_indexes) + 1:02d}"
                unique_indexes[k] = {
                    "num": idx_num,
                    "name": nm,
                    "table": tbl,
                    "columns": r.get("columns", ""),
                    "ddl": f"CREATE NONCLUSTERED INDEX [{nm}] ON [{tbl}] ({r.get('columns', '')}) WITH (ONLINE = ON);",
                    "is_active": True,
                    "matching_live": [nm],
                    "queries": ["(Genel DMV İndeksi)"]
                }

        # ---------------------------------------------------------------------
        # 1. POPULATE QUERY - INDEX MAPPING TABLE (self.table_idx_mgmt)
        # ---------------------------------------------------------------------
        self.table_idx_mgmt.setRowCount(len(queries_to_display))

        for row_idx, item in enumerate(queries_to_display):
            q_id = item["id"]
            query_sql = item["query_sql"]
            target_table = item["target_table"]
            has_applied_idx = bool(item.get("applied_index"))

            idx_meta = unique_indexes.get(query_matched_idx_key.get(q_id))
            has_index = idx_meta["is_active"] if idx_meta else False
            idx_num_str = idx_meta["num"] if idx_meta else "—"

            bench_ms = get_latest_benchmark(q_id)
            current_ms = None
            multiplier = None
            speedup_pct = None

            # If benchmark exists or query was already executed WITH an index:
            if has_index:
                if bench_ms is not None:
                    current_ms = bench_ms
                elif has_applied_idx and item.get("initial_ms") is not None:
                    current_ms = item["initial_ms"]

            # Determine baseline (unindexed execution time)
            baseline_ms = get_latest_baseline(q_id)
            if baseline_ms is None:
                if not has_applied_idx and not has_index:
                    baseline_ms = item.get("initial_ms")
                else:
                    baseline_ms = None

            if has_index and current_ms is not None and baseline_ms is not None:
                if baseline_ms > 0 and current_ms < baseline_ms:
                    speedup_pct = round(((baseline_ms - current_ms) / baseline_ms) * 100.0, 1)
                    multiplier = round(baseline_ms / current_ms, 1)
                else:
                    speedup_pct = 0.0
                    multiplier = 1.0
            else:
                speedup_pct = None
                multiplier = None


            # 0. Title & Table
            it_0 = QTableWidgetItem(f"{item['title']}\nTablo: [{target_table}]")
            it_0.setForeground(QColor(self.c("text_primary")))
            self.table_idx_mgmt.setItem(row_idx, 0, it_0)

            # 1. SQL Query Summary (Expandable / Collapsible)
            sql_cell = self.create_expandable_sql_cell(f"mgmt_{q_id}", query_sql, self.table_idx_mgmt, max_collapsed_len=60)
            self.table_idx_mgmt.setCellWidget(row_idx, 1, sql_cell)

            # 2. Matched Index Number Badge
            if idx_meta:
                it_2 = QTableWidgetItem(f"● {idx_num_str} ({idx_meta['name']})")
                it_2.setForeground(QColor(self.c("accent_success")) if has_index else QColor(self.c("accent_warning")))
                it_2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                tooltip_txt = (
                    f"{idx_num_str} Detayı:\n"
                    f"• İndeks Adı: [{idx_meta['name']}]\n"
                    f"• Hedef Tablo: {idx_meta['table']}\n"
                    f"• Kolonlar: ({idx_meta['columns']})\n"
                    f"• Durum: {'SQL Server Üzerinde Aktif' if has_index else 'Önerilen (Oluşturulmadı)'}\n"
                    f"• DDL Tanımı:\n{idx_meta['ddl']}"
                )
                it_2.setToolTip(tooltip_txt)
            else:
                it_2 = QTableWidgetItem("—")
                it_2.setForeground(QColor(self.c("text_muted")))
                it_2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_idx_mgmt.setItem(row_idx, 2, it_2)

            # 3. Before MS
            it_3 = QTableWidgetItem(f"{baseline_ms} ms" if baseline_ms else "—")
            it_3.setForeground(QColor(self.c("accent_danger")))
            it_3.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_idx_mgmt.setItem(row_idx, 3, it_3)

            # 4. After MS
            if has_index:
                after_str = f"{current_ms} ms" if current_ms is not None else "Ölçüm Bekliyor"
                it_4 = QTableWidgetItem(after_str)
                it_4.setForeground(QColor(self.c("accent_success")) if current_ms is not None else QColor(self.c("accent_warning")))
            else:
                after_str = "İndekssiz"
                it_4 = QTableWidgetItem(after_str)
                it_4.setForeground(QColor(self.c("text_muted")))
            it_4.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_idx_mgmt.setItem(row_idx, 4, it_4)

            # 5. Speedup Ratio
            if has_index and multiplier is not None:
                gain_str = f"{multiplier}x (+%{speedup_pct})"
                it_5 = QTableWidgetItem(gain_str)
                it_5.setForeground(QColor(self.c("accent_success")))
            else:
                gain_str = "—"
                it_5 = QTableWidgetItem(gain_str)
                it_5.setForeground(QColor(self.c("text_muted")))
            it_5.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_idx_mgmt.setItem(row_idx, 5, it_5)

            # 6. Actions (İndeksle / Test / Sil)
            btn_cell = QWidget()
            btn_layout = QHBoxLayout(btn_cell)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)

            item_pass = {
                "id": item["id"],
                "title": item["title"],
                "table": target_table,
                "query_sql": query_sql,
                "recommended_sql": idx_meta["ddl"] if idx_meta else "",
                "recommended_name": idx_meta["name"] if idx_meta else "",
                "has_index": has_index,
                "active_indexes": idx_meta["matching_live"] if idx_meta else [],
            }

            if not has_index:
                b_apply = QPushButton(t("index.btn_apply"))
                b_apply.setProperty("class", "btn-success")
                b_apply.setCursor(Qt.CursorShape.PointingHandCursor)
                b_apply_style = """
                    QPushButton { background-color: #059669; color: #ffffff; border: 1px solid #047857; font-weight: 800; font-size: 11px; border-radius: 2px; padding: 3px 8px; }
                    QPushButton:hover { background-color: #047857; border-color: #065f46; color: #ffffff; }
                    QPushButton:pressed { background-color: #064e3b; }
                """ if self.is_light_theme else """
                    QPushButton { background-color: #065f46; color: #ffffff; border: 1px solid #10b981; font-weight: 800; font-size: 11px; border-radius: 2px; padding: 3px 8px; }
                    QPushButton:hover { background-color: #047857; border-color: #6ee7b7; color: #ffffff; }
                    QPushButton:pressed { background-color: #064e3b; }
                """
                b_apply.setStyleSheet(b_apply_style)
                b_apply.setMinimumWidth(80)
                b_apply.setMinimumHeight(24)
                b_apply.clicked.connect(lambda checked, it=item_pass: self.apply_index_only(it))
                btn_layout.addWidget(b_apply)
            else:
                b_test = QPushButton(t("index.btn_test"))
                b_test.setProperty("class", "btn-warning")
                b_test.setCursor(Qt.CursorShape.PointingHandCursor)
                b_test_style = """
                    QPushButton { background-color: #d97706; color: #ffffff; border: 1px solid #b45309; font-weight: 800; font-size: 11px; border-radius: 2px; padding: 3px 6px; }
                    QPushButton:hover { background-color: #b45309; border-color: #92400e; color: #ffffff; }
                    QPushButton:pressed { background-color: #78350f; }
                """ if self.is_light_theme else """
                    QPushButton { background-color: #854d0e; color: #ffffff; border: 1px solid #f59e0b; font-weight: 800; font-size: 11px; border-radius: 2px; padding: 3px 6px; }
                    QPushButton:hover { background-color: #a16207; border-color: #fde68a; color: #ffffff; }
                    QPushButton:pressed { background-color: #713f12; }
                """
                b_test.setStyleSheet(b_test_style)
                b_test.setMinimumWidth(55)
                b_test.setMinimumHeight(24)
                b_test.clicked.connect(lambda checked, it=item_pass: self.benchmark_single_index_query(it))
                btn_layout.addWidget(b_test)

                b_drop = QPushButton(t("index.btn_delete"))
                b_drop.setProperty("class", "btn-danger")
                b_drop.setCursor(Qt.CursorShape.PointingHandCursor)
                b_drop_style = """
                    QPushButton { background-color: #e11d48; color: #ffffff; border: 1px solid #be123c; font-weight: 800; font-size: 11px; border-radius: 2px; padding: 3px 6px; }
                    QPushButton:hover { background-color: #be123c; border-color: #9f1239; color: #ffffff; }
                    QPushButton:pressed { background-color: #881337; }
                """ if self.is_light_theme else """
                    QPushButton { background-color: #881337; color: #ffffff; border: 1px solid #f43f5e; font-weight: 800; font-size: 11px; border-radius: 2px; padding: 3px 6px; }
                    QPushButton:hover { background-color: #9f1239; border-color: #fecdd3; color: #ffffff; }
                    QPushButton:pressed { background-color: #4c0519; }
                """
                b_drop.setStyleSheet(b_drop_style)
                b_drop.setMinimumWidth(50)
                b_drop.setMinimumHeight(24)
                b_drop.clicked.connect(lambda checked, it=item_pass: self.drop_single_index_row(it["active_indexes"][0], it["table"]))
                btn_layout.addWidget(b_drop)


            self.table_idx_mgmt.setCellWidget(row_idx, 6, btn_cell)

        self.table_idx_mgmt.resizeRowsToContents()

        # ---------------------------------------------------------------------
        # 2. POPULATE NUMBERED INDEX CATALOG TABLE (self.table_idx_catalog)
        # ---------------------------------------------------------------------
        catalog_list = list(unique_indexes.values())
        self.table_idx_catalog.setRowCount(len(catalog_list))

        for c_idx, meta in enumerate(catalog_list):
            # 0. Index Number
            it_c0 = QTableWidgetItem(meta["num"])
            it_c0.setForeground(QColor(self.c("accent_cyan")))
            it_c0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_idx_catalog.setItem(c_idx, 0, it_c0)

            # 1. Index Name & Table
            it_c1 = QTableWidgetItem(f"[{meta['name']}]\nTablo: {meta['table']}" if get_language() == "tr" else f"[{meta['name']}]\nTable: {meta['table']}")
            it_c1.setForeground(QColor(self.c("text_primary")))
            self.table_idx_catalog.setItem(c_idx, 1, it_c1)

            # 2. Status
            it_c2 = QTableWidgetItem(t("index.status_active") if meta["is_active"] else t("index.status_rec"))
            it_c2.setForeground(QColor(self.c("accent_success")) if meta["is_active"] else QColor(self.c("accent_warning")))
            it_c2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_idx_catalog.setItem(c_idx, 2, it_c2)

            # 3. Columns & DDL
            ddl_preview = f"Kolonlar: ({meta['columns']})\n{meta['ddl']}" if get_language() == "tr" else f"Columns: ({meta['columns']})\n{meta['ddl']}"
            it_c3 = QTableWidgetItem(ddl_preview)
            it_c3.setForeground(QColor(self.c("accent_success")) if meta["is_active"] else QColor(self.c("text_secondary")))
            self.table_idx_catalog.setItem(c_idx, 3, it_c3)

            # 4. Queries Using This Index
            q_count = len(meta["queries"])
            q_summary = f"{', '.join(meta['queries'])}\n({q_count} Sorgu Paylaşıyor)" if get_language() == "tr" else f"{', '.join(meta['queries'])}\n({q_count} Queries Sharing)"
            it_c4 = QTableWidgetItem(q_summary)
            it_c4.setForeground(QColor(self.c("text_secondary")))
            self.table_idx_catalog.setItem(c_idx, 4, it_c4)


            # 5. Actions
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)
            act_layout.setSpacing(4)

            cat_item = {
                "id": f"cat_{c_idx}",
                "title": meta["num"],
                "table": meta["table"],
                "query_sql": "",
                "recommended_sql": meta["ddl"],
                "recommended_name": meta["name"],
                "has_index": meta["is_active"],
                "active_indexes": meta["matching_live"],
            }

            if not meta["is_active"]:
                b_c_apply = QPushButton(t("index.btn_create_idx"))
                b_c_apply.setProperty("class", "btn-success")
                b_c_apply.setCursor(Qt.CursorShape.PointingHandCursor)
                b_c_apply_style = """
                    QPushButton { background-color: #059669; color: #ffffff; border: 1px solid #047857; font-weight: 800; font-size: 11px; border-radius: 2px; padding: 3px 10px; }
                    QPushButton:hover { background-color: #047857; border-color: #065f46; color: #ffffff; }
                    QPushButton:pressed { background-color: #064e3b; }
                """ if self.is_light_theme else """
                    QPushButton { background-color: #065f46; color: #ffffff; border: 1px solid #10b981; font-weight: 800; font-size: 11px; border-radius: 2px; padding: 3px 10px; }
                    QPushButton:hover { background-color: #047857; border-color: #6ee7b7; color: #ffffff; }
                    QPushButton:pressed { background-color: #064e3b; }
                """
                b_c_apply.setStyleSheet(b_c_apply_style)
                b_c_apply.setMinimumWidth(125)
                b_c_apply.setMinimumHeight(24)
                b_c_apply.clicked.connect(lambda checked, it=cat_item: self.apply_index_only(it))
                act_layout.addWidget(b_c_apply)
            else:
                b_c_drop = QPushButton(t("index.btn_drop_idx"))
                b_c_drop.setProperty("class", "btn-danger")
                b_c_drop.setCursor(Qt.CursorShape.PointingHandCursor)
                b_c_drop_style = """
                    QPushButton { background-color: #e11d48; color: #ffffff; border: 1px solid #be123c; font-weight: 800; font-size: 11px; border-radius: 2px; padding: 3px 10px; }
                    QPushButton:hover { background-color: #be123c; border-color: #9f1239; color: #ffffff; }
                    QPushButton:pressed { background-color: #881337; }
                """ if self.is_light_theme else """
                    QPushButton { background-color: #881337; color: #ffffff; border: 1px solid #f43f5e; font-weight: 800; font-size: 11px; border-radius: 2px; padding: 3px 10px; }
                    QPushButton:hover { background-color: #9f1239; border-color: #fecdd3; color: #ffffff; }
                    QPushButton:pressed { background-color: #4c0519; }
                """
                b_c_drop.setStyleSheet(b_c_drop_style)
                b_c_drop.setMinimumWidth(125)
                b_c_drop.setMinimumHeight(24)
                b_c_drop.clicked.connect(lambda checked, it=cat_item: self.drop_single_index_row(it["active_indexes"][0], it["table"]))
                act_layout.addWidget(b_c_drop)






            self.table_idx_catalog.setCellWidget(c_idx, 5, act_widget)


        self.table_idx_catalog.resizeRowsToContents()


    def apply_index_only(self, item, show_dialog: bool = True):
        try:
            conn = get_connection(autocommit=True)
            with conn.cursor() as cur:
                cur.execute(item["recommended_sql"])
            conn.close()

            record_applied_index(item["recommended_name"], item["table"], [], item["recommended_sql"], "İndeks Yönetimi sekmesi")
            record_decision("applied_index", f"Oluşturuldu: [{item['recommended_name']}] ON [{item['table']}]")

            if show_dialog:
                self.show_toast("İNDEKS OLUŞTURULDU", f"[{item['recommended_name']}] indeksi SQL Server üzerinde başarıyla oluşturuldu!\nPerformansı test etmek için [Test] butonuna basabilirsiniz.", "success")
            self.load_index_mgmt_table()
            self.refresh_mgmt_page()
        except Exception as e:
            if show_dialog:
                self.show_toast("İNDEKS OLUŞTURMA HATASI", str(e), "danger")


    def benchmark_single_index_query(self, item, show_dialog=True):
        query_sql = item["query_sql"]
        target_table = item.get("table", "") or ("orders" if "orders" in query_sql.lower() else ("customers" if "customers" in query_sql.lower() else ""))
        times = []
        try:
            from src.db_connection import measure_query_server_time
        except ImportError:
            from db_connection import measure_query_server_time

        try:
            # 1. Always execute unindexed version (force Table Scan) to measure and record baseline
            import re
            def _inject_table_scan_hint(sql_text: str, tbl_target: str = "") -> str:
                clean_s = re.sub(r",\s*INDEX\s*\([^)]*\)", "", sql_text, flags=re.IGNORECASE)
                clean_s = re.sub(r"\bINDEX\s*\([^)]*\)\s*,?", "", clean_s, flags=re.IGNORECASE)
                clean_s = re.sub(r"\bWITH\s*\(\s*\)", "", clean_s, flags=re.IGNORECASE)
                ctes = {c.lower() for c in re.findall(r"\b(?:WITH|,)\s*\[?(\w+)\]?\s+AS\s*\(", clean_s, re.IGNORECASE)}
                t_pat = re.escape(tbl_target.strip("[] ")) if tbl_target else r"\w+"

                def _rep(m):
                    verb, tbl, alias, existing_with = m.group(1), m.group(2), m.group(3) or "", m.group(4)
                    t_clean = re.sub(r"\W+", "", tbl.split(".")[-1]).lower()
                    if t_clean in ctes or t_clean in ("where", "on", "join", "group", "order", "inner", "left", "right", "outer", "cross", "select", "apply"):
                        return m.group(0)
                    alias_str = f" {alias}" if alias and alias.lower() not in ("with", "where", "on", "join", "group", "order", "inner", "left", "right", "outer", "cross", "as") else ""
                    if existing_with:
                        with_hints = [h.strip() for h in existing_with.split(",") if h.strip() and not h.strip().upper().startswith("INDEX")]
                        with_hints.append("INDEX(0)")
                        new_with = f" WITH ({', '.join(with_hints)})"
                    else:
                        new_with = " WITH (INDEX(0))"
                    return f"{verb} {tbl}{alias_str}{new_with}"

                if tbl_target:
                    pat = re.compile(rf"\b(FROM|JOIN)\s+((?:\[?\w+\]?\.)?\[?{t_pat}\]?)(?:\s+(?:AS\s+)?\[?(\w+)\]?)?(?:\s+WITH\s*\(([^)]*)\))?", re.IGNORECASE)
                    new_sql, count = pat.subn(_rep, clean_s, count=1)
                    if count > 0:
                        return new_sql

                pat_gen = re.compile(r"\b(FROM)\s+((?:\[?\w+\]?\.)?\[?\w+\]?)(?:\s+(?:AS\s+)?\[?(\w+)\]?)?(?:\s+WITH\s*\(([^)]*)\))?", re.IGNORECASE)
                new_sql, count = pat_gen.subn(_rep, clean_s, count=1)
                return new_sql

            unindexed_sql = _inject_table_scan_hint(query_sql, target_table)

            if unindexed_sql:
                tagged_unindexed = f"-- VTX_BENCHMARK_TEST\n{unindexed_sql}"
                u_ms, _ = measure_query_server_time(tagged_unindexed)
                if u_ms and u_ms > 0:
                    record_baseline(item["id"], round(u_ms, 2))

            # 2. Measure indexed execution time
            tagged_indexed = f"-- VTX_BENCHMARK_TEST\n{query_sql}"
            for _ in range(3):
                s_ms, _ = measure_query_server_time(tagged_indexed)
                times.append(s_ms)

            times.sort()
            measured = round(times[1], 2)
            record_benchmark(item["id"], measured, measured, "single_bench")

            if show_dialog:
                b_now = get_latest_baseline(item["id"])
                if b_now and b_now > measured:
                    mult = round(b_now / measured, 1)
                    pct = round(((b_now - measured) / b_now) * 100, 1)
                    self.show_toast("BENCHMARK TAMAMLANDI", f"[{item['title']}]\nİndekssiz: {b_now} ms ➔ İndeksli: {measured} ms ({mult}x Hızlı, %{pct} Kazanç)", "info")
                else:
                    self.show_toast("BENCHMARK TAMAMLANDI", f"[{item['title']}] saf motor süresi: {measured} ms", "info")
            self.load_index_mgmt_table()
            self.refresh_mgmt_page()
        except Exception as e:
            if show_dialog:
                self.show_toast("BENCHMARK HATASI", str(e), "danger")


    def drop_single_index_row(self, idx_name, table_name):
        ret = QMessageBox.question(self, "İndeksi Sil", f"[{idx_name}] indeksi SQL Server'dan kaldırılacak. Onaylıyor musunuz?")
        if ret != QMessageBox.StandardButton.Yes:
            return

        try:
            conn = get_connection(autocommit=True)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT SCHEMA_NAME(t.schema_id) AS schemaname, t.name AS tablename
                    FROM sys.indexes i
                    JOIN sys.tables t ON t.object_id = i.object_id
                    WHERE i.name = %s
                """, (idx_name,))
                rows = cur.fetchall()
                if rows:
                    target_schema = rows[0][0] if isinstance(rows[0], (list, tuple)) else rows[0]["schemaname"]
                    target_table = rows[0][1] if isinstance(rows[0], (list, tuple)) else rows[0]["tablename"]
                    cur.execute(f"DROP INDEX [{idx_name}] ON [{target_schema}].[{target_table}]")
                elif table_name:
                    if "." in str(table_name):
                        parts = [p.strip("[] ") for p in str(table_name).split(".", 1)]
                        cur.execute(f"DROP INDEX IF EXISTS [{idx_name}] ON [{parts[0]}].[{parts[1]}]")
                    else:
                        cur.execute(f"DROP INDEX IF EXISTS [{idx_name}] ON [{table_name}]")
                try:
                    cur.execute("DBCC FREEPROCCACHE")
                    cur.execute("DBCC DROPCLEANBUFFERS")
                except Exception:
                    pass
            conn.close()

            from src.state_store import record_index_rolled_back
            record_index_rolled_back(idx_name)
            record_decision("manual_drop", f"Silindi: [{idx_name}] on [{table_name}]")
            self.load_index_mgmt_table()
            self.refresh_mgmt_page()
            self.show_toast("İNDEKS SİLİNDİ", f"[{idx_name}] indeksi SQL Server'dan silindi ve RAM önbelleği temizlendi.", "danger")
        except Exception as e:
            self.show_toast("SİLME HATASI", str(e), "danger")



    # -------------------------------------------------------------------------
    # PAGE 4: YÖNETİM & TELEMETRİ (Active Auto-updating Telemetry, Engine Toggle & Clear Audit)
    # -------------------------------------------------------------------------
    def create_mgmt_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)

        # 4 Telemetry Stat Cards
        cards_grid = QHBoxLayout()
        cards_grid.setSpacing(12)

        self.sc_custom = StatCard(t("mgmt.stat_custom_title"), "0 Active" if get_language() == "en" else "0 Aktif", "SQL Server Nonclustered DDL", icon_name="fa5s.layer-group", accent_color="#10b981")
        cards_grid.addWidget(self.sc_custom)

        self.sc_queries = StatCard(t("mgmt.stat_queries_title"), "0 Queries" if get_language() == "en" else "0 Sorgu", t("mgmt.stat_queries_sub"), icon_name="fa5s.search", accent_color="#06b6d4")
        cards_grid.addWidget(self.sc_queries)

        self.sc_speedup = StatCard(t("mgmt.stat_speedup_title"), "0.0x (+0%)" if get_language() == "en" else "0.0x (+%0)", t("mgmt.stat_speedup_none_sub"), icon_name="fa5s.tachometer-alt", accent_color="#10b981")
        cards_grid.addWidget(self.sc_speedup)

        self.sc_engine = StatCard(t("mgmt.stat_engine_title"), t("mgmt.stat_engine_active_val"), t("mgmt.stat_engine_active_sub"), icon_name="fa5s.shield-alt", accent_color="#06b6d4")
        cards_grid.addWidget(self.sc_engine)

        layout.addLayout(cards_grid)

        # Safety & Motor Control Card
        info_card = QFrame()
        info_card.setProperty("class", "card-panel")
        ic_layout = QHBoxLayout(info_card)
        ic_layout.setContentsMargins(16, 14, 16, 14)
        ic_layout.setSpacing(16)

        # Left Engine Toggle Switch
        l_motor = QVBoxLayout()
        self.lbl_mgmt_engine_ctrl = QLabel(t("mgmt.engine_ctrl_title"))
        l_motor.addWidget(self.lbl_mgmt_engine_ctrl)
        self.btn_toggle_engine = QPushButton(t("mgmt.btn_engine_active") if self.engine_active else t("mgmt.btn_engine_inactive"))
        self.btn_toggle_engine.setStyleSheet("background: #041a12; border: 1px solid #10b981; color: #6ee7b7; font-weight: 800; padding: 7px 14px; font-family: 'JetBrains Mono', monospace;")
        self.btn_toggle_engine.clicked.connect(self.toggle_engine_state)
        l_motor.addWidget(self.btn_toggle_engine)
        ic_layout.addLayout(l_motor)

        # Middle Info: Last action
        m_info = QVBoxLayout()
        self.lbl_mgmt_last_action_title = QLabel(t("mgmt.last_action_title"))
        m_info.addWidget(self.lbl_mgmt_last_action_title)
        self.lbl_last_action = QLabel(t("mgmt.last_action_none"))
        self.lbl_last_action.setStyleSheet(f"color: {self.c('text_primary')}; font-weight: 700; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        m_info.addWidget(self.lbl_last_action)
        ic_layout.addLayout(m_info, 1)


        # Right Safety & Quota Control
        r_info = QVBoxLayout()
        self.lbl_mgmt_quota_title = QLabel(t("mgmt.quota_title"))
        r_info.addWidget(self.lbl_mgmt_quota_title)
        q_row = QHBoxLayout()
        self.lbl_mgmt_quota_label = QLabel(t("mgmt.quota_label"))
        self.lbl_mgmt_quota_label.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 11px;")
        q_row.addWidget(self.lbl_mgmt_quota_label)

        self.spin_quota_mgmt = QuotaStepperWidget(value=self.max_indexes_limit, min_val=1, max_val=20)
        self.spin_quota_mgmt.valueChanged.connect(self.set_max_indexes_quota)
        q_row.addWidget(self.spin_quota_mgmt)
        r_info.addLayout(q_row)

        self.lbl_mgmt_safety_strip = QLabel(t("mgmt.safety_strip"))
        self.lbl_mgmt_safety_strip.setStyleSheet("color: #94a3b8; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        r_info.addWidget(self.lbl_mgmt_safety_strip)
        ic_layout.addLayout(r_info, 1)

        layout.addWidget(info_card)

        # Lower Split: Audit Trail Table vs Terminal Logs
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Audit Trail
        audit_card = QFrame()
        audit_card.setProperty("class", "card-panel")
        a_layout = QVBoxLayout(audit_card)
        a_layout.setContentsMargins(12, 12, 12, 12)
        
        a_head = QHBoxLayout()
        self.lbl_mgmt_audit_title = QLabel(t("mgmt.audit_title"))
        a_head.addWidget(self.lbl_mgmt_audit_title)
        a_head.addStretch()

        self.btn_clear_audit = QPushButton(t("mgmt.btn_clear_audit"))
        self.btn_clear_audit.clicked.connect(self.clear_audit_trail_prompt)
        a_head.addWidget(self.btn_clear_audit)
        a_layout.addLayout(a_head)

        self.table_decisions = QTableWidget()
        self.table_decisions.setColumnCount(3)
        self.table_decisions.setHorizontalHeaderLabels([t("mgmt.audit_col_type"), t("mgmt.audit_col_details"), t("mgmt.audit_col_time")])
        self.table_decisions.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_decisions.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_decisions.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        a_layout.addWidget(self.table_decisions)
        splitter.addWidget(audit_card)

        # Terminal Logs
        term_card = QFrame()
        term_card.setProperty("class", "card-panel")
        t_layout = QVBoxLayout(term_card)
        t_layout.setContentsMargins(12, 12, 12, 12)
        self.lbl_mgmt_telemetry_title = QLabel(t("mgmt.telemetry_title"))
        t_layout.addWidget(self.lbl_mgmt_telemetry_title)

        self.term_log = QPlainTextEdit()
        self.term_log.setReadOnly(True)
        self.term_log.setPlainText("[Ready] Engine telemetry and live DMV stream will be shown here...\n" if get_language() == "en" else "[Hazır] Motor telemetri ve canlı DMV akışı burada gösterilir...\n")
        t_layout.addWidget(self.term_log)
        splitter.addWidget(term_card)

        layout.addWidget(splitter, 1)
        return page

    def clear_audit_trail_prompt(self):
        ret = QMessageBox.question(self, t("mgmt.btn_clear_audit"), "All autonomous decision records will be deleted. Are you sure?" if get_language() == "en" else "Tüm otonom karar kayıtları silinecektir. Onaylıyor musunuz?")
        if ret == QMessageBox.StandardButton.Yes:
            clear_agent_decisions()
            self.refresh_mgmt_page()
            self.show_toast(t("toast.all_cleared_title"), "Autonomous decision history cleared." if get_language() == "en" else "Otonom karar geçmişi başarıyla temizlendi.", "info")

    def refresh_mgmt_page(self):
        DEFAULT_SCHEMA_INDEXES = {"idx_orders_customer_id", "idx_customers_email"}
        q_idx = """
            SELECT t.name AS table_name, i.name AS index_name
            FROM sys.indexes i
            JOIN sys.tables t ON t.object_id = i.object_id
            WHERE t.is_ms_shipped = 0 AND i.name IS NOT NULL 
              AND i.is_primary_key = 0 AND i.is_unique_constraint = 0
        """
        all_active_rows = execute_query(q_idx) or [] if self.is_connected else []
        custom_rows = [r for r in all_active_rows if r["index_name"] not in DEFAULT_SCHEMA_INDEXES]

        captured = get_captured_queries()
        captured_count = len(captured)

        # Update StatCards with i18n
        self.sc_custom.set_title(t("mgmt.stat_custom_title"))
        self.sc_custom.set_value(t("mgmt.stat_custom_val", count=len(custom_rows)), t("mgmt.stat_custom_sub", count=len(custom_rows)))

        self.sc_queries.set_title(t("mgmt.stat_queries_title"))
        self.sc_queries.set_value(t("mgmt.stat_queries_val", count=captured_count), t("mgmt.stat_queries_sub"))

        self.sc_speedup.set_title(t("mgmt.stat_speedup_title"))
        if not custom_rows or not captured:
            self.sc_speedup.set_value(t("mgmt.stat_speedup_none_val"), t("mgmt.stat_speedup_none_sub"))
        else:
            self.sc_speedup.set_value(t("mgmt.stat_speedup_active_val"), t("mgmt.stat_speedup_active_sub", count=len(custom_rows)))

        self.sc_engine.set_title(t("mgmt.stat_engine_title"))
        if self.engine_active:
            self.sc_engine.set_value(t("mgmt.stat_engine_active_val"), t("mgmt.stat_engine_active_sub"))
        else:
            self.sc_engine.set_value(t("mgmt.stat_engine_stopped_val"), t("mgmt.stat_engine_stopped_sub"))

        # Decisions
        decisions = get_recent_decisions(15)
        applied = [d for d in decisions if "applied" in d.decision_type or "create" in d.details.lower()]
        if applied:
            self.lbl_last_action.setText(f"{applied[0].details} ({applied[0].created_at})")
        else:
            self.lbl_last_action.setText(t("mgmt.last_action_none"))

        self.table_decisions.setRowCount(len(decisions))
        for r_idx, dec in enumerate(decisions):
            it_type = QTableWidgetItem(dec.decision_type)
            it_type.setForeground(QColor(self.c("accent_cyan")))
            self.table_decisions.setItem(r_idx, 0, it_type)

            it_det = QTableWidgetItem(dec.details)
            it_det.setForeground(QColor(self.c("text_primary")))
            self.table_decisions.setItem(r_idx, 1, it_det)

            it_time = QTableWidgetItem(dec.created_at[:19])
            it_time.setForeground(QColor(self.c("text_muted")))
            self.table_decisions.setItem(r_idx, 2, it_time)

        self.table_decisions.resizeRowsToContents()



    # -------------------------------------------------------------------------
    # GLOBAL WORKERS & STREAMING
    # -------------------------------------------------------------------------
    def log_line(self, line: str):
        self.term_log.appendPlainText(line)

    def run_remediate_worker(self):
        self.term_log.appendPlainText("\n❯ Tüm İndeksleri Otomatik Uygulama Başlatılıyor...")
        self.current_worker = RemediateWorker(dry_run=False)
        self.current_worker.log_signal.connect(self.log_line)
        self.current_worker.finished_signal.connect(self.on_worker_finished)
        self.current_worker.start()

    def run_benchmark_worker(self):
        self.term_log.appendPlainText("\n❯ Tüm Sorguları Canlı Benchmark Etme Başlatılıyor...")
        self.current_worker = BenchmarkWorker()
        self.current_worker.log_signal.connect(self.log_line)
        self.current_worker.finished_signal.connect(self.on_worker_finished)
        self.current_worker.start()

    def run_reset_worker(self):
        ret = QMessageBox.warning(self, "İndeksleri Sıfırla", "SQL Server üzerindeki tüm özel optimizasyon indeksleri kaldırılacak. Onaylıyor musunuz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        self.term_log.appendPlainText("\n❯ Tüm Özel İndeksleri Sıfırlama Başlatılıyor...")
        self.current_worker = ResetWorker()
        self.current_worker.log_signal.connect(self.log_line)
        self.current_worker.finished_signal.connect(self.on_worker_finished)
        self.current_worker.start()

    def on_worker_finished(self, success: bool = True, message: str = ""):
        self.refresh_all()
        if message:
            toast_type = "success" if success else "danger"
            if "SIFIRLAMA" in message or "Sıfırlama" in message:
                toast_type = "danger"
            elif "BENCHMARK" in message or "Benchmark" in message:
                toast_type = "info"
            title = "İŞLEM BAŞARILI" if success else "İŞLEM HATASI"
            self.show_toast(title, message.strip(), toast_type)


    def set_max_indexes_quota(self, val: int):
        self.max_indexes_limit = val
        if hasattr(self, "spin_quota_idx") and self.spin_quota_idx.value() != val:
            self.spin_quota_idx.blockSignals(True)
            self.spin_quota_idx.setValue(val)
            self.spin_quota_idx.blockSignals(False)
        if hasattr(self, "spin_quota_mgmt") and self.spin_quota_mgmt.value() != val:
            self.spin_quota_mgmt.blockSignals(True)
            self.spin_quota_mgmt.setValue(val)
            self.spin_quota_mgmt.blockSignals(False)
        self.run_autonomous_optimizer_tick()

    def run_autonomous_optimizer_tick(self):
        """Autonomous optimization engine: evaluates workload and ensures TOP N optimum indexes are applied."""
        if not self.engine_active or not self.is_connected:
            return

        try:
            persisted = get_captured_queries()
            if not persisted:
                return

            # Score recommendations across all captured queries
            candidate_scores = {}
            for q in persisted:
                raw_sql = q.get("query_sql", "").strip()
                tbl = q.get("target_table", "orders")
                init_ms = float(q.get("initial_ms") or 50.0)
                rec = recommend_index_for_query(raw_sql)
                if not rec or rec.table in ("sys", "system", "user_table") or rec.table.startswith("sys") or rec.index_name.startswith("idx_sys_"):
                    continue

                actual_table = rec.table or tbl
                if actual_table in ("sys", "system", "user_table") or actual_table.startswith("sys"):
                    continue

                idx_key = (actual_table, rec.index_name)
                if idx_key not in candidate_scores:
                    candidate_scores[idx_key] = {
                        "name": rec.index_name,
                        "table": actual_table,
                        "ddl": rec.create_statement,
                        "columns": rec.columns,
                        "score": 0.0,
                        "query_count": 0,
                    }
                candidate_scores[idx_key]["score"] += init_ms
                candidate_scores[idx_key]["query_count"] += 1

            if not candidate_scores:
                return

            # Sort candidate indexes by impact score descending
            ranked = sorted(candidate_scores.values(), key=lambda x: (x["score"], x["query_count"]), reverse=True)
            top_optimum = ranked[:self.max_indexes_limit]
            top_names = {item["name"] for item in top_optimum}

            # Fetch active custom non-clustered indexes on SQL Server
            active_custom = []
            try:
                conn = get_connection(autocommit=True)
                with conn.cursor(as_dict=True) as cur:
                    cur.execute("""
                        SELECT i.name AS index_name, t.name AS table_name, SCHEMA_NAME(t.schema_id) AS schema_name
                        FROM sys.indexes i
                        JOIN sys.tables t ON i.object_id = t.object_id
                        WHERE i.is_primary_key = 0 
                          AND i.is_unique_constraint = 0 
                          AND i.type_desc = 'NONCLUSTERED'
                          AND i.name NOT IN ('idx_orders_customer_id', 'idx_customers_email')
                    """)
                    active_custom = cur.fetchall() or []
                conn.close()
            except Exception:
                return

            active_names = {r["index_name"] for r in active_custom}

            # 1. Apply any missing top optimum index up to quota
            newly_applied = []
            for opt in top_optimum:
                if opt["name"] not in active_names and len(active_names) < self.max_indexes_limit:
                    try:
                        conn = get_connection(autocommit=True)
                        with conn.cursor() as cur:
                            cur.execute(opt["ddl"])
                        conn.close()

                        record_applied_index(opt["name"], opt["table"], opt["columns"], opt["ddl"], "Otonom Motor (Top Optimum)")
                        record_decision("autonomous_apply", f"Otonom İndeks Uygulandı: [{opt['name']}] ON [{opt['table']}] (Kota: {self.max_indexes_limit})")
                        active_names.add(opt["name"])
                        newly_applied.append(opt["name"])
                        self.term_log.appendPlainText(f"⚡ [OTONOM MOTOR]: Optimum İndeks [{opt['name']}] SQL Server'a uygulandı (Kota: {self.max_indexes_limit}).")
                    except Exception as e:
                        self.term_log.appendPlainText(f"⚠ [OTONOM MOTOR HATASI]: [{opt['name']}] oluşturulamadı: {e}")

            # 2. If active indexes exceed quota, automatically prune active indexes not in top_optimum
            if len(active_names) > self.max_indexes_limit:
                for act in active_custom:
                    if len(active_names) <= self.max_indexes_limit:
                        break
                    nm = act["index_name"]
                    tbl = act["table_name"]
                    sch = act.get("schema_name", "dbo")
                    if nm not in top_names:
                        try:
                            conn = get_connection(autocommit=True)
                            with conn.cursor() as cur:
                                cur.execute(f"DROP INDEX [{nm}] ON [{sch}].[{tbl}]")
                                try:
                                    cur.execute("DBCC FREEPROCCACHE")
                                    cur.execute("DBCC DROPCLEANBUFFERS")
                                except Exception:
                                    pass
                            conn.close()
                            from src.state_store import record_index_rolled_back
                            record_index_rolled_back(nm)
                            record_decision("autonomous_prune", f"Kota Dengeleme: [{nm}] kaldırıldı.")
                            active_names.discard(nm)
                            self.term_log.appendPlainText(f"🗑 [OTONOM KOTA DÜZENLEME]: Kota sınırı ({self.max_indexes_limit}) için önceliği düşük [{nm}] indeksi kaldırıldı.")
                        except Exception:
                            pass

            if newly_applied:
                self.show_toast("OTONOM İNDEKS UYGULANDI", f"{len(newly_applied)} adet optimum indeks otomatik olarak SQL Server'a uygulandı (Kota: {self.max_indexes_limit}).", "success")
                self.load_index_mgmt_table()
                self.refresh_mgmt_page()

        except Exception:
            pass

    # -------------------------------------------------------------------------
    # AUTO-REFRESH & HEALTH MONITORING (Runs every 3 seconds)
    # -------------------------------------------------------------------------
    def auto_refresh(self):
        cfg = get_config()
        reachable = is_server_reachable(cfg.database.host, cfg.database.port, timeout_sec=0.5)
        self.is_connected = reachable

        if reachable:
            self.lbl_health_box.setText(f"ONLINE | :{cfg.database.port}")
            self.lbl_health_box.setStyleSheet(f"font-size: 11px; font-weight: 800; font-family: 'JetBrains Mono', monospace; padding: 5px 12px; background: {self.c('badge_online_bg')}; color: {self.c('badge_online_text')}; border: 1px solid {self.c('badge_online_border')}; border-radius: 2px;")
            
            # Live DMV query sniffing & autonomous optimization if engine is active
            if self.engine_active:
                try:
                    new_qs = poll_and_capture_live_dmv_queries()
                    if new_qs:
                        self.term_log.appendPlainText(f"⚡ [CANLI DMV YAKALANDI]: {len(new_qs)} yeni sorgu yakalandı ({new_qs[0]['query_sql'][:50]}...)")
                    # Run autonomous optimizer pass
                    self.run_autonomous_optimizer_tick()
                except Exception:
                    pass
        else:
            self.lbl_health_box.setText("OFFLINE | BAĞLANTI YOK")
            self.lbl_health_box.setStyleSheet(f"font-size: 11px; font-weight: 800; font-family: 'JetBrains Mono', monospace; padding: 5px 12px; background: {self.c('badge_offline_bg')}; color: {self.c('badge_offline_text')}; border: 1px solid {self.c('badge_offline_border')}; border-radius: 2px;")


        cur_idx = self.stacked_widget.currentIndex()
        if cur_idx == 0:
            self.refresh_connect_page()
        elif cur_idx == 2:
            self.load_queries_only_table()
        elif cur_idx == 3:
            self.load_index_mgmt_table()
        elif cur_idx == 4:
            self.refresh_mgmt_page()

    def refresh_all(self):
        self.auto_refresh()