"""Custom Cyber Quota Stepper Widget for VortexDBA with Light/Dark Theme Support."""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal


class QuotaStepperWidget(QWidget):
    """Modern Cyber Quota Step Selector with [-] and [+] buttons and glowing badge."""
    valueChanged = pyqtSignal(int)

    def __init__(self, value: int = 5, min_val: int = 1, max_val: int = 20, is_light: bool = False, parent: QWidget = None):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self._value = max(min_val, min(max_val, value))
        self._is_light = is_light

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Minus button [-]
        self.btn_minus = QPushButton("−")
        self.btn_minus.setFixedSize(28, 28)
        self.btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_minus.clicked.connect(self._decrement)
        layout.addWidget(self.btn_minus)

        # Center Display Badge
        self.lbl_display = QLabel(f"{self._value} İNDEKS")
        self.lbl_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_display.setFixedHeight(28)
        self.lbl_display.setMinimumWidth(85)
        layout.addWidget(self.lbl_display)

        # Plus button [+]
        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedSize(28, 28)
        self.btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_plus.clicked.connect(self._increment)
        layout.addWidget(self.btn_plus)

        self.apply_theme(self._is_light)

    def apply_theme(self, is_light: bool):
        self._is_light = is_light
        if is_light:
            btn_style = """
                QPushButton {
                    background-color: #f1f5f9;
                    border: 1px solid #cbd5e1;
                    color: #0284c7;
                    font-size: 15px;
                    font-weight: 900;
                    border-radius: 2px;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: #e0f2fe;
                    border-color: #0284c7;
                    color: #0369a1;
                }
                QPushButton:pressed {
                    background-color: #bae6fd;
                }
            """
            lbl_style = """
                QLabel {
                    background-color: #ffffff;
                    border: 1px solid #0284c7;
                    color: #0284c7;
                    font-size: 11.5px;
                    font-weight: 800;
                    font-family: 'JetBrains Mono', monospace;
                    padding: 2px 8px;
                    border-radius: 2px;
                }
            """
        else:
            btn_style = """
                QPushButton {
                    background-color: #0c1527;
                    border: 1px solid #1e3a8a;
                    color: #38bdf8;
                    font-size: 15px;
                    font-weight: 900;
                    border-radius: 2px;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: #1e3a8a;
                    border-color: #38bdf8;
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: #0284c7;
                }
            """
            lbl_style = """
                QLabel {
                    background-color: #040814;
                    border: 1px solid #0284c7;
                    color: #38bdf8;
                    font-size: 11.5px;
                    font-weight: 800;
                    font-family: 'JetBrains Mono', monospace;
                    padding: 2px 8px;
                    border-radius: 2px;
                }
            """
        self.btn_minus.setStyleSheet(btn_style)
        self.btn_plus.setStyleSheet(btn_style)
        self.lbl_display.setStyleSheet(lbl_style)

    def value(self) -> int:
        return self._value

    def setValue(self, val: int):
        val = max(self.min_val, min(self.max_val, val))
        if val != self._value:
            self._value = val
            self.lbl_display.setText(f"{self._value} İNDEKS")

    def _decrement(self):
        if self._value > self.min_val:
            self._value -= 1
            self.lbl_display.setText(f"{self._value} İNDEKS")
            self.valueChanged.emit(self._value)

    def _increment(self):
        if self._value < self.max_val:
            self._value += 1
            self.lbl_display.setText(f"{self._value} İNDEKS")
            self.valueChanged.emit(self._value)
