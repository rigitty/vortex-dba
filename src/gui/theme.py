"""Professional Compact Black & Blue Dark Theme Stylesheet for PyQt6."""

DARK_THEME_QSS = """
/* Global Application Styles */
QWidget {
    background-color: #06090f;
    color: #e2e8f0;
    font-family: "Segoe UI", "Inter", -apple-system, sans-serif;
    font-size: 11px;
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
}

/* Main Window */
QMainWindow {
    background-color: #06090f;
}

/* Scroll Area */
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* Custom Minimal Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #06090f;
    width: 6px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #192333;
    min-height: 20px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background: #2563eb;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #06090f;
    height: 6px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #192333;
    min-width: 20px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover {
    background: #2563eb;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Solid Cards & Frames (Smooth rounded corners) */
QFrame.card-panel {
    background-color: #0b111c;
    border: 1px solid #162234;
    border-radius: 6px;
}

QFrame.header-panel {
    background-color: #080d17;
    border-bottom: 1px solid #141d2c;
}

/* Standard Buttons */
QPushButton {
    background-color: #0f1827;
    border: 1px solid #1c2c44;
    color: #cbd5e1;
    border-radius: 5px;
    padding: 5px 11px;
    font-weight: 600;
    font-size: 11px;
}
QPushButton:hover {
    background-color: #16243a;
    border-color: #2563eb;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #0b1320;
    border-color: #1d4ed8;
}
QPushButton:disabled {
    background-color: #090e18;
    border-color: #121b29;
    color: #475569;
}

/* Primary Blue Action Button */
QPushButton.btn-primary, QPushButton.btn-success {
    background-color: #2563eb;
    border: 1px solid #3b82f6;
    color: #ffffff;
    font-weight: 600;
}
QPushButton.btn-primary:hover, QPushButton.btn-success:hover {
    background-color: #1d4ed8;
    border-color: #60a5fa;
}
QPushButton.btn-primary:pressed, QPushButton.btn-success:pressed {
    background-color: #1e40af;
}

/* Secondary Blue Action Button */
QPushButton.btn-secondary {
    background-color: #0f1d33;
    border: 1px solid #1d3d6e;
    color: #93c5fd;
    font-weight: 600;
}
QPushButton.btn-secondary:hover {
    background-color: #142744;
    border-color: #2563eb;
    color: #ffffff;
}

/* Warning Action Button (Restrained Dark Slate / Subtle Amber) */
QPushButton.btn-warning {
    background-color: #141c2c;
    border: 1px solid #233550;
    color: #93c5fd;
    font-weight: 600;
}
QPushButton.btn-warning:hover {
    background-color: #1c2b42;
    border-color: #3b82f6;
    color: #ffffff;
}

/* Danger / Reset Button (Subtle Dark Slate / Controlled) */
QPushButton.btn-danger {
    background-color: #151620;
    border: 1px solid #311c24;
    color: #fca5a5;
    font-weight: 600;
}
QPushButton.btn-danger:hover {
    background-color: #261720;
    border-color: #ef4444;
    color: #ffffff;
}

/* Segmented Control Buttons */
QPushButton.segment-btn {
    background-color: transparent;
    border: none;
    color: #8393a7;
    padding: 3px 9px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 10.5px;
}
QPushButton.segment-btn:hover {
    background-color: #121c2c;
    color: #f1f5f9;
}
QPushButton.segment-btn:checked {
    background-color: #17263d;
    color: #60a5fa;
    border: 1px solid #2563eb;
}

/* Input Fields */
QLineEdit, QSpinBox {
    background-color: #05080e;
    border: 1px solid #182335;
    border-radius: 5px;
    padding: 4px 8px;
    color: #f1f5f9;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 11px;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #2563eb;
    background-color: #070c16;
}

/* Labels */
QLabel {
    background-color: transparent;
    color: #e2e8f0;
}
QLabel.label-muted {
    color: #8092a7;
    font-size: 10px;
}
QLabel.label-title {
    font-size: 13px;
    font-weight: 700;
    color: #ffffff;
}

/* Table Widget */
QTableWidget {
    background-color: #080d16;
    border: 1px solid #152030;
    border-radius: 6px;
    gridline-color: #0f1826;
    color: #e2e8f0;
    selection-background-color: #14233a;
    selection-color: #ffffff;
    font-size: 11px;
}
QTableWidget::item {
    padding: 4px 6px;
    border-bottom: 1px solid #0e1624;
}
QTableWidget::item:hover {
    background-color: #0d1624;
}
QHeaderView::section {
    background-color: #090e18;
    color: #7d90a6;
    padding: 6px 8px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: none;
    border-bottom: 1px solid #162335;
    border-right: 1px solid #0d1522;
}

/* PlainTextEdit (Terminal) */
QPlainTextEdit {
    background-color: #04060b;
    border: 1px solid #141e2d;
    border-radius: 6px;
    padding: 8px;
    color: #cbd5e1;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 10.5px;
    line-height: 1.4;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #162335;
    border-radius: 6px;
    background-color: #080d16;
    top: -1px;
}
QTabBar::tab {
    background-color: #090e17;
    border: 1px solid #162335;
    color: #8294a8;
    padding: 6px 14px;
    margin-right: 3px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    font-weight: 600;
    font-size: 11px;
}
QTabBar::tab:selected {
    background-color: #101b2c;
    color: #60a5fa;
    border-bottom: 2px solid #2563eb;
}
QTabBar::tab:hover:!selected {
    background-color: #0c1422;
    color: #ffffff;
}

/* Dialog */
QDialog {
    background-color: #080d17;
    border: 1px solid #162335;
    border-radius: 8px;
}

/* Status Bar */
QStatusBar {
    background-color: #05080e;
    border-top: 1px solid #121a28;
    color: #64748b;
    font-size: 10px;
    padding: 2px 8px;
}
"""

