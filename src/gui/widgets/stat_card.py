"""Shadcn UI styled Stat Metric Card Widget for PyQt6 with Theme Support."""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
import qtawesome as qta


class StatCard(QFrame):
    """Compact metric card with clean typography and rounded corners."""
    def __init__(self, title: str, initial_value: str = "0", subtitle: str = "", icon_name: str = "fa5s.layer-group", accent_color: str = "#3b82f6", parent=None):
        super().__init__(parent)
        self.setProperty("class", "card-panel")
        self.setMinimumHeight(68)
        self.accent_color = accent_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        # Top row: Title and Icon
        top_row = QHBoxLayout()
        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setStyleSheet("font-size: 9.5px; font-weight: 700; color: #728499; letter-spacing: 0.5px;")
        top_row.addWidget(self.title_lbl)
        top_row.addStretch()

        self.icon_lbl = QLabel()
        try:
            icon = qta.icon(icon_name, color=accent_color)
            self.icon_lbl.setPixmap(icon.pixmap(14, 14))
        except Exception:
            pass
        top_row.addWidget(self.icon_lbl)
        layout.addLayout(top_row)

        # Middle: Value
        self.value_lbl = QLabel(initial_value)
        self.value_lbl.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {accent_color}; font-family: 'JetBrains Mono', monospace;")
        layout.addWidget(self.value_lbl)

        # Bottom: Subtitle
        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setStyleSheet("font-size: 9.5px; color: #54687d;")
        layout.addWidget(self.sub_lbl)

    def apply_theme(self, is_light: bool):
        if is_light:
            self.title_lbl.setStyleSheet("font-size: 9.5px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
            self.sub_lbl.setStyleSheet("font-size: 9.5px; color: #94a3b8;")
        else:
            self.title_lbl.setStyleSheet("font-size: 9.5px; font-weight: 700; color: #728499; letter-spacing: 0.5px;")
            self.sub_lbl.setStyleSheet("font-size: 9.5px; color: #54687d;")

    def set_value(self, val: str, subtitle: str = None):
        self.value_lbl.setText(val)
        if subtitle is not None:
            self.sub_lbl.setText(subtitle)

    def set_title(self, title: str):
        self.title_lbl.setText(title.upper())

