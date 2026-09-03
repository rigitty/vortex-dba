"""Segmented Language Toggle Button [ EN | TR ] for PyQt6."""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal


class LanguageToggle(QWidget):
    """Sleek segmented language selector toggle for EN / TR."""
    language_changed = pyqtSignal(str)

    def __init__(self, current_lang: str = "en", is_light: bool = False, parent: QWidget = None):
        super().__init__(parent)
        self.current_lang = "tr" if current_lang == "tr" else "en"
        self.is_light = is_light

        self.setFixedSize(70, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)

        self.btn_en = QPushButton("EN")
        self.btn_en.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_en.clicked.connect(lambda: self.set_language("en"))
        layout.addWidget(self.btn_en)

        self.btn_tr = QPushButton("TR")
        self.btn_tr.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tr.clicked.connect(lambda: self.set_language("tr"))
        layout.addWidget(self.btn_tr)

        self.update_visuals()

    def set_language(self, lang: str):
        lang = "tr" if lang == "tr" else "en"
        if self.current_lang != lang:
            self.current_lang = lang
            self.update_visuals()
            self.language_changed.emit(self.current_lang)

    def set_theme(self, is_light: bool):
        self.is_light = is_light
        self.update_visuals()

    def update_visuals(self):
        container_bg = "#e2e8f0" if self.is_light else "#0c0c16"
        container_border = "#cbd5e1" if self.is_light else "#1e1e2e"

        active_bg = "#0284c7" if self.is_light else "#1d4ed8"
        active_color = "#ffffff"
        
        inactive_color = "#64748b" if self.is_light else "#8b8b9e"
        inactive_hover = "#0f172a" if self.is_light else "#f8fafc"

        self.setStyleSheet(f"""
            LanguageToggle {{
                background-color: {container_bg};
                border: 1px solid {container_border};
                border-radius: 4px;
            }}
        """)

        base_btn_style = """
            QPushButton {
                font-family: 'JetBrains Mono', monospace;
                font-size: 10px;
                font-weight: 800;
                border: none;
                border-radius: 3px;
                padding: 0px;
            }
        """

        if self.current_lang == "en":
            self.btn_en.setStyleSheet(base_btn_style + f"""
                QPushButton {{
                    background-color: {active_bg};
                    color: {active_color};
                }}
            """)
            self.btn_tr.setStyleSheet(base_btn_style + f"""
                QPushButton {{
                    background-color: transparent;
                    color: {inactive_color};
                }}
                QPushButton:hover {{
                    color: {inactive_hover};
                }}
            """)
        else:
            self.btn_en.setStyleSheet(base_btn_style + f"""
                QPushButton {{
                    background-color: transparent;
                    color: {inactive_color};
                }}
                QPushButton:hover {{
                    color: {inactive_hover};
                }}
            """)
            self.btn_tr.setStyleSheet(base_btn_style + f"""
                QPushButton {{
                    background-color: {active_bg};
                    color: {active_color};
                }}
            """)
