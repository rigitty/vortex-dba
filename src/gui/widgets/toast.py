"""Persistent Floating Toast Notification system for PyQt6."""
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor


class ToastCard(QFrame):
    """A persistent floating toast card with a manual close [✖] button."""
    closed_signal = pyqtSignal(object)

    THEMES = {
        "success": {
            "border": "#10b981",
            "accent": "#10b981",
            "bg": "#041510",
            "title_color": "#34d399",
            "icon": "✔"
        },
        "danger": {
            "border": "#f43f5e",
            "accent": "#f43f5e",
            "bg": "#18040a",
            "title_color": "#fb7185",
            "icon": "🗑"
        },
        "warning": {
            "border": "#f59e0b",
            "accent": "#f59e0b",
            "bg": "#180e03",
            "title_color": "#fbbf24",
            "icon": "⚠"
        },
        "info": {
            "border": "#06b6d4",
            "accent": "#06b6d4",
            "bg": "#03141a",
            "title_color": "#38bdf8",
            "icon": "⚡"
        }
    }

    def __init__(self, title: str, message: str, toast_type: str = "success", parent: QWidget = None):
        super().__init__(parent)
        self.toast_type = toast_type if toast_type in self.THEMES else "info"
        style = self.THEMES[self.toast_type]

        self.setFixedWidth(360)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {style['bg']};
                border: 1px solid {style['border']};
                border-left: 4px solid {style['accent']};
                border-radius: 2px;
            }}
        """)

        # Drop shadow for depth
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 10, 10)
        layout.setSpacing(6)

        # Header Row: Icon + Title + Time + Close [✖]
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        icon_lbl = QLabel(style["icon"])
        icon_lbl.setStyleSheet(f"color: {style['title_color']}; font-size: 14px; font-weight: 800; background: transparent; border: none;")
        top_row.addWidget(icon_lbl)

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(f"color: {style['title_color']}; font-size: 11.5px; font-weight: 800; font-family: 'JetBrains Mono', monospace; background: transparent; border: none;")
        top_row.addWidget(title_lbl, 1)

        time_str = datetime.now().strftime("%H:%M:%S")
        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-family: 'JetBrains Mono', monospace; background: transparent; border: none;")
        top_row.addWidget(time_lbl)

        # Close button
        btn_close = QPushButton("✖")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setFixedSize(20, 20)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #9494a8;
                font-size: 11px;
                font-weight: 700;
                padding: 0;
            }
            QPushButton:hover {
                color: #ffffff;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
            }
        """)
        btn_close.clicked.connect(self.close_toast)
        top_row.addWidget(btn_close)

        layout.addLayout(top_row)

        # Message Text
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #e2e8f0; font-size: 11px; font-family: 'JetBrains Mono', 'Segoe UI', sans-serif; background: transparent; border: none; line-height: 1.3;")
        layout.addWidget(msg_lbl)

        # Auto-close timer after 5 seconds
        self._closing = False
        self.auto_timer = QTimer(self)
        self.auto_timer.setSingleShot(True)
        self.auto_timer.timeout.connect(self.close_toast)
        self.auto_timer.start(5000)

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

    def add_toast(self, title: str, message: str, toast_type: str = "success") -> ToastCard:
        card = ToastCard(title, message, toast_type, self)
        card.closed_signal.connect(self._on_toast_closed)
        self.layout.addWidget(card)
        self.reposition()
        self.show()
        self.raise_()
        return card

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
