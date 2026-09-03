"""Professional Boxy Pure Black Theme Stylesheet for PyQt6."""

DARK_THEME_QSS = """
/* Global Application Styles */
QWidget {
    background-color: #000000;
    color: #e2e8f0;
    font-family: "JetBrains Mono", "Segoe UI", "Inter", -apple-system, sans-serif;
    font-size: 11.5px;
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
}

/* Main Window */
QMainWindow {
    background-color: #000000;
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
    background: #000000;
    width: 6px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #192333;
    min-height: 20px;
    border-radius: 0px;
}
QScrollBar::handle:vertical:hover {
    background: #2563eb;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #000000;
    height: 6px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #192333;
    min-width: 20px;
    border-radius: 0px;
}
QScrollBar::handle:horizontal:hover {
    background: #2563eb;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Solid Cards & Frames (Strictly Boxy) */
QFrame.card-panel {
    background-color: #07070a;
    border: 1px solid #1a1a24;
    border-radius: 0px;
}

QFrame.header-panel {
    background-color: #07070a;
    border-bottom: 1px solid #1a1a24;
}

/* Standard Buttons */
QPushButton {
    background-color: #0c0c12;
    border: 1px solid #242434;
    color: #cbd5e1;
    border-radius: 0px;
    padding: 6px 14px;
    font-weight: 700;
    font-size: 11px;
    font-family: "JetBrains Mono", monospace;
    text-transform: uppercase;
}
QPushButton:hover {
    background-color: #151520;
    border-color: #3b3b52;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #000000;
    border-color: #2563eb;
}
QPushButton:disabled {
    background-color: #050508;
    border-color: #14141c;
    color: #475569;
}

/* Primary Blue Action Button */
QPushButton.btn-primary {
    background-color: #1e3a8a;
    border: 1px solid #3b82f6;
    color: #ffffff;
    font-weight: 700;
}
QPushButton.btn-primary:hover {
    background-color: #2563eb;
    border-color: #60a5fa;
}

/* Success Green Action Button */
QPushButton.btn-success {
    background-color: #064e3b;
    border: 1px solid #10b981;
    color: #6ee7b7;
    font-weight: 700;
}
QPushButton.btn-success:hover {
    background-color: #047857;
    color: #ffffff;
}

/* Warning Amber Action Button */
QPushButton.btn-warning {
    background-color: #78350f;
    border: 1px solid #f59e0b;
    color: #fde68a;
    font-weight: 700;
}
QPushButton.btn-warning:hover {
    background-color: #b45309;
    color: #ffffff;
}

/* Danger Red Button */
QPushButton.btn-danger {
    background-color: #881337;
    border: 1px solid #f43f5e;
    color: #fecdd3;
    font-weight: 700;
}
QPushButton.btn-danger:hover {
    background-color: #be123c;
    color: #ffffff;
}

/* Top Nav Tab Button */
QPushButton.nav-tab-btn {
    background-color: transparent;
    border: 1px solid transparent;
    color: #9494a8;
    padding: 7px 15px;
    font-weight: 700;
    font-size: 11px;
    font-family: "JetBrains Mono", monospace;
    text-transform: uppercase;
}
QPushButton.nav-tab-btn:hover {
    background-color: #0e0e16;
    color: #ffffff;
}
QPushButton.nav-tab-btn:checked {
    background-color: #141420;
    color: #ffffff;
    border: 1px solid #2a2a38;
}

/* Input Fields */
QLineEdit, QSpinBox {
    background-color: #020204;
    border: 1px solid #1a1a24;
    border-radius: 0px;
    padding: 6px 10px;
    color: #f1f5f9;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #06b6d4;
    background-color: #05050a;
}

/* Labels */
QLabel {
    background-color: transparent;
    color: #e2e8f0;
}
QLabel.label-muted {
    color: #64748b;
    font-size: 10.5px;
}
QLabel.label-title {
    font-size: 13px;
    font-weight: 700;
    color: #ffffff;
    font-family: "JetBrains Mono", monospace;
}

/* Table Widget */
QTableWidget {
    background-color: #020204;
    border: 1px solid #1a1a24;
    border-radius: 0px;
    gridline-color: #111118;
    color: #e2e8f0;
    selection-background-color: #141424;
    selection-color: #ffffff;
    font-size: 11.5px;
    font-family: "JetBrains Mono", "Segoe UI", sans-serif;
}
QTableWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #0e0e16;
}
QTableWidget::item:hover {
    background-color: #0a0a12;
}
QHeaderView::section {
    background-color: #050508;
    color: #8b8b9e;
    padding: 8px 10px;
    font-size: 10.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: none;
    border-bottom: 1px solid #1a1a24;
    border-right: 1px solid #0e0e14;
    font-family: "JetBrains Mono", monospace;
}

/* PlainTextEdit (SQL Editor & Terminal) */
QPlainTextEdit {
    background-color: #020204;
    border: 1px solid #1a1a24;
    border-radius: 0px;
    padding: 10px 12px;
    color: #93c5fd;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 11.5px;
    line-height: 1.45;
}
QPlainTextEdit:focus {
    border-color: #06b6d4;
    background-color: #040408;
}

/* Tab Widget (if used directly) */
QTabWidget::pane {
    border: 1px solid #1a1a24;
    background-color: #000000;
    border-radius: 0px;
}
QTabBar::tab {
    background-color: #07070a;
    border: 1px solid #1a1a24;
    color: #8b8b9e;
    padding: 7px 16px;
    font-weight: 700;
    font-size: 11px;
    font-family: "JetBrains Mono", monospace;
}
QTabBar::tab:selected {
    background-color: #141420;
    color: #ffffff;
    border-bottom: 2px solid #06b6d4;
}
"""