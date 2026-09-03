"""Persistent Floating Toast Notification system for PyQt6 with Full Dark & Light Theme support."""
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor


class ToastCard(QFrame):
    """A persistent floating toast card with a manual close [✖] button, fully theme-adaptive."""
    closed_signal = pyqtSignal(object)

    THEMES_DARK = {
        "success": {
            "border": "#059669",
            "accent": "#10b981",
            "bg": "#041a12",
            "title_color": "#34d399",
            "msg_color": "#e2e8f0",
            "time_color": "#64748b",
            "close_color": "#9494a8",
            "close_hover": "#ffffff",
            "icon": "✔"
        },
        "danger": {
            "border": "#be123c",
            "accent": "#f43f5e",
            "bg": "#18040a",
            "title_color": "#fb7185",
            "msg_color": "#e2e8f0",
            "time_color": "#64748b",
            "close_color": "#9494a8",
            "close_hover": "#ffffff",
            "icon": "🗑"
        },
        "warning": {
            "border": "#b45309",
            "accent": "#f59e0b",
            "bg": "#180e03",
            "title_color": "#fbbf24",
            "msg_color": "#e2e8f0",
            "time_color": "#64748b",
            "close_color": "#9494a8",
            "close_hover": "#ffffff",
            "icon": "⚠"
        },
        "info": {
            "border": "#0891b2",
            "accent": "#06b6d4",
            "bg": "#03141a",
            "title_color": "#38bdf8",
            "msg_color": "#e2e8f0",
            "time_color": "#64748b",
            "close_color": "#9494a8",
            "close_hover": "#ffffff",
            "icon": "⚡"
        }
    }

    THEMES_LIGHT = {
        "success": {
            "border": "#86efac",
            "accent": "#059669",
            "bg": "#f0fdf4",
            "title_color": "#047857",
            "msg_color": "#0f172a",
            "time_color": "#475569",
            "close_color": "#64748b",
            "close_hover": "#0f172a",
            "icon": "✔"
        },
        "danger": {
            "border": "#fecdd3",
            "accent": "#e11d48",
            "bg": "#fff1f2",
            "title_color": "#be123c",
            "msg_color": "#0f172a",
            "time_color": "#475569",
            "close_color": "#64748b",
            "close_hover": "#0f172a",
            "icon": "🗑"
        },
        "warning": {
            "border": "#fde68a",
            "accent": "#d97706",
            "bg": "#fffbeb",
            "title_color": "#b45309",
            "msg_color": "#0f172a",
            "time_color": "#475569",
            "close_color": "#64748b",
            "close_hover": "#0f172a",
            "icon": "⚠"
        },
        "info": {
            "border": "#bae6fd",
            "accent": "#0284c7",
            "bg": "#f0f9ff",
            "title_color": "#0369a1",
            "msg_color": "#0f172a",
            "time_color": "#475569",
            "close_color": "#64748b",
            "close_hover": "#0f172a",
            "icon": "⚡"
        }
    }

    def __init__(self, title: str, message: str, toast_type: str = "success", is_light: bool = False, parent: QWidget = None):
        super().__init__(parent)
        self.toast_type = toast_type if toast_type in self.THEMES_DARK else "info"
        self.is_light = is_light
        self.title_text = title
        self.message_text = message

        self.setFixedWidth(360)

        # Drop shadow for clean floating depth
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(16)
        self.shadow.setColor(QColor(0, 0, 0, 40 if is_light else 180))
        self.shadow.setOffset(0, 4)
        self.setGraphicsEffect(self.shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 10, 10)
        layout.setSpacing(6)

        # Header Row: Icon + Title + Time + Close [✖]
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.icon_lbl = QLabel()
        top_row.addWidget(self.icon_lbl)

        self.title_lbl = QLabel(title.upper())
        top_row.addWidget(self.title_lbl, 1)

        time_str = datetime.now().strftime("%H:%M:%S")
        self.time_lbl = QLabel(time_str)
        top_row.addWidget(self.time_lbl)

        # Close button
        self.btn_close = QPushButton("✖")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.clicked.connect(self.close_toast)
        top_row.addWidget(self.btn_close)

        layout.addLayout(top_row)

        # Message Text
        self.msg_lbl = QLabel(message)
        self.msg_lbl.setWordWrap(True)
        layout.addWidget(self.msg_lbl)

        self.apply_theme(is_light)

        # Auto-close timer after 5 seconds
        self._closing = False
        self.auto_timer = QTimer(self)
        self.auto_timer.setSingleShot(True)
        self.auto_timer.timeout.connect(self.close_toast)
        self.auto_timer.start(5000)

    def apply_theme(self, is_light: bool):
        """Re-applies visual styles for the active theme."""
        self.is_light = is_light
        style = self.THEMES_LIGHT[self.toast_type] if is_light else self.THEMES_DARK[self.toast_type]

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {style['bg']};
                border: 1px solid {style['border']};
                border-left: 4px solid {style['accent']};
                border-radius: 3px;
            }}
        """)

        if hasattr(self, "shadow"):
            self.shadow.setColor(QColor(0, 0, 0, 45 if is_light else 180))

        self.icon_lbl.setText(style["icon"])
        self.icon_lbl.setStyleSheet(f"color: {style['title_color']}; font-size: 14px; font-weight: 800; background: transparent; border: none;")

        self.title_lbl.setStyleSheet(f"color: {style['title_color']}; font-size: 11.5px; font-weight: 800; font-family: 'JetBrains Mono', monospace; background: transparent; border: none;")

        self.time_lbl.setStyleSheet(f"color: {style['time_color']}; font-size: 10px; font-family: 'JetBrains Mono', monospace; background: transparent; border: none;")

        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {style['close_color']};
                font-size: 11px;
                font-weight: 700;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {style['close_hover']};
                background: rgba(0, 0, 0, 0.08) if {str(is_light).lower()} else rgba(255, 255, 255, 0.1);
                border-radius: 2px;
            }}
        """)

        self.msg_lbl.setStyleSheet(f"color: {style['msg_color']}; font-size: 11px; font-family: 'JetBrains Mono', 'Segoe UI', sans-serif; background: transparent; border: none; line-height: 1.3;")

    def close_toast(self):
        if getattr(self, "_closing", False):
            return
        self._closing = True
        if hasattr(self, "auto_timer"):
            self.auto_timer.stop()
        self.closed_signal.emit(self)
        self.deleteLater()


class ToastOverlay(QWidget):
    """Floating container for stackable persistent toasts pinned to the bottom-right."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFixedWidth(380)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 16, 16)
        self.layout.setSpacing(8)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

    def add_toast(self, title: str, message: str, toast_type: str = "success", is_light: bool = False) -> ToastCard:
        card = ToastCard(title, message, toast_type, is_light=is_light, parent=self)
        card.closed_signal.connect(self._on_toast_closed)
        self.layout.addWidget(card)
        self.reposition()
        self.show()
        self.raise_()
        return card

    def set_theme(self, is_light: bool):
        """Updates all currently active toast cards to the specified theme."""
        for i in range(self.layout.count()):
            item = self.layout.itemAt(i)
            w = item.widget()
            if isinstance(w, ToastCard):
                w.apply_theme(is_light)

    def _on_toast_closed(self, card: ToastCard):
        self.layout.removeWidget(card)
        self.reposition()
        if self.layout.count() == 0:
            self.hide()

    def reposition(self):
        if not self.parent():
            return
        p_rect = self.parent().rect()
        h = min(p_rect.height() - 60, max(120, self.layout.sizeHint().height() + 20))
        w = 380
        x = p_rect.width() - w - 10
        y = p_rect.height() - h - 10
        self.setGeometry(x, y, w, h)
        self.raise_()
