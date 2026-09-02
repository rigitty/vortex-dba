"""Shadcn UI styled Stat Metric Card Widget for PyQt6."""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
import qtawesome as qta


class StatCard(QFrame):
    """A sleek metric card displaying title, big value, subtitle and icon."""
    def __init__(self, title: str, initial_value: str = "0", subtitle: str = "", icon_name: str = "fa5s.layer-group", accent_color: str = "#38bdf8", parent=None):
        super().__init__(parent)
        self.setProperty("class", "card-panel")
        self.setMinimumHeight(115)
        self.accent_color = accent_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        # Top row: Title and Icon
        top_row = QHBoxLayout()
        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px;")
        top_row.addWidget(self.title_lbl)
        top_row.addStretch()

        self.icon_lbl = QLabel()
        try:
            icon = qta.icon(icon_name, color=accent_color)
            self.icon_lbl.setPixmap(icon.pixmap(20, 20))
        except Exception:
            pass
        top_row.addWidget(self.icon_lbl)
        layout.addLayout(top_row)

        # Middle: Big Value
        self.value_lbl = QLabel(initial_value)
        self.value_lbl.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {accent_color}; font-family: 'JetBrains Mono', monospace;")
        layout.addWidget(self.value_lbl)

        # Bottom: Subtitle
        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        layout.addWidget(self.sub_lbl)

    def set_value(self, val: str, subtitle: str = None):
        self.value_lbl.setText(val)
        if subtitle is not None:
            self.sub_lbl.setText(subtitle)
