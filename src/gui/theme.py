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
    background-color: #0c0c14;
    border: 1px solid #2a2a3c;
    color: #e2e8f0;
    border-radius: 2px;
    padding: 8px 16px;
    font-weight: 700;
    font-size: 11.5px;
    font-family: "JetBrains Mono", monospace;
    text-transform: uppercase;
}
QPushButton:hover {
    background-color: #161624;
    border-color: #4b4b66;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #050508;
    border-color: #38bdf8;
}
QPushButton:disabled {
    background-color: #050508;
    border-color: #14141c;
    color: #475569;
}

/* Primary Blue Action Button (With Blue Glow) */
QPushButton.btn-primary {
    background-color: #1d4ed8;
    border: 1px solid #3b82f6;
    color: #ffffff;
    font-weight: 800;
    font-size: 11.5px;
    padding: 8px 18px;
}
QPushButton.btn-primary:hover {
    background-color: #2563eb;
    border: 1px solid #93c5fd;
    color: #ffffff;
}
QPushButton.btn-primary:pressed {
    background-color: #1e40af;
    border: 1px solid #bfdbfe;
}

/* Success Green Action Button (With Emerald Glow) */
QPushButton.btn-success {
    background-color: #065f46;
    border: 1px solid #10b981;
    color: #ecfdf5;
    font-weight: 800;
    font-size: 11.5px;
    padding: 8px 18px;
}
QPushButton.btn-success:hover {
    background-color: #047857;
    border: 1px solid #6ee7b7;
    color: #ffffff;
}
QPushButton.btn-success:pressed {
    background-color: #064e3b;
    border: 1px solid #a7f3d0;
}

/* Warning Amber Action Button (With Amber Glow) */
QPushButton.btn-warning {
    background-color: #854d0e;
    border: 1px solid #f59e0b;
    color: #fffbeb;
    font-weight: 800;
    font-size: 11.5px;
    padding: 8px 18px;
}
QPushButton.btn-warning:hover {
    background-color: #a16207;
    border: 1px solid #fde68a;
    color: #ffffff;
}
QPushButton.btn-warning:pressed {
    background-color: #713f12;
    border: 1px solid #fef3c7;
}

/* Danger Red Button (With Rose Glow) */
QPushButton.btn-danger {
    background-color: #881337;
    border: 1px solid #f43f5e;
    color: #fff1f2;
    font-weight: 800;
    font-size: 11.5px;
    padding: 8px 18px;
}
QPushButton.btn-danger:hover {
    background-color: #9f1239;
    border: 1px solid #fecdd3;
    color: #ffffff;
}
QPushButton.btn-danger:pressed {
    background-color: #4c0519;
    border: 1px solid #ffe4e6;
}

/* Top Nav Tab Button (With Glowing Active State) */
QPushButton.nav-tab-btn {
    background-color: transparent;
    border: 1px solid transparent;
    color: #9494a8;
    padding: 8px 18px;
    font-weight: 800;
    font-size: 12px;
    font-family: "JetBrains Mono", monospace;
    text-transform: uppercase;
    border-radius: 2px;
}
QPushButton.nav-tab-btn:hover {
    background-color: #0c1728;
    color: #ffffff;
    border: 1px solid #1e3a8a;
}
QPushButton.nav-tab-btn:checked {
    background-color: #0c213d;
    color: #38bdf8;
    border: 1px solid #38bdf8;
    font-weight: 800;
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