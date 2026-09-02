"""Modern Shadcn UI / Linear Dark Theme Stylesheet for PyQt6."""

DARK_THEME_QSS = """
/* Global Application Styles */
QWidget {
    background-color: #080c14;
    color: #f1f5f9;
    font-family: "Segoe UI", "Plus Jakarta Sans", "Inter", sans-serif;
    font-size: 13px;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
}

/* Main Window */
QMainWindow {
    background-color: #080c14;
}

/* Scroll Area */
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* Custom Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #080c14;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #1e293b;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #38bdf8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #080c14;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #1e293b;
    min-width: 24px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #38bdf8;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Frames and Panels */
QFrame.card-panel {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
}

QFrame.header-panel {
    background-color: #0c121e;
    border-bottom: 1px solid #1e293b;
}

/* Buttons */
QPushButton {
    background-color: #162032;
    border: 1px solid #283548;
    color: #f8fafc;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #1e2c45;
    border-color: #38bdf8;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #0f172a;
}
QPushButton:disabled {
    background-color: #0f1420;
    border-color: #1e2638;
    color: #475569;
}

/* Success Button (Step 2 - Emerald) */
QPushButton.btn-success {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #059669);
    border: 1px solid #34d399;
    color: #ffffff;
    font-weight: 700;
}
QPushButton.btn-success:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34d399, stop:1 #10b981);
    border-color: #6ee7b7;
}

/* Warning Button (Step 3 - Amber) */
QPushButton.btn-warning {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d97706, stop:1 #b45309);
    border: 1px solid #fbbf24;
    color: #ffffff;
    font-weight: 700;
}
QPushButton.btn-warning:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f59e0b, stop:1 #d97706);
    border-color: #fde68a;
}

/* Danger Button (Step 5 - Rose) */
QPushButton.btn-danger {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e11d48, stop:1 #be123c);
    border: 1px solid #f87171;
    color: #ffffff;
    font-weight: 700;
}
QPushButton.btn-danger:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f43f5e, stop:1 #e11d48);
}

/* Segmented Control Buttons */
QPushButton.segment-btn {
    background-color: transparent;
    border: none;
    color: #94a3b8;
    padding: 5px 12px;
    border-radius: 6px;
    font-weight: 600;
}
QPushButton.segment-btn:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: #ffffff;
}
QPushButton.segment-btn:checked {
    background-color: #1e293b;
    color: #38bdf8;
    border: 1px solid #38bdf8;
}

/* Input Fields */
QLineEdit, QSpinBox {
    background-color: #060911;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 7px 12px;
    color: #f8fafc;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #38bdf8;
    background-color: #090e18;
}

/* Labels */
QLabel {
    background-color: transparent;
    color: #f1f5f9;
}
QLabel.label-muted {
    color: #94a3b8;
    font-size: 11px;
}
QLabel.label-title {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
}

/* Table Widget */
QTableWidget {
    background-color: #0b1019;
    border: 1px solid #1e293b;
    border-radius: 12px;
    gridline-color: #151f30;
    color: #f1f5f9;
    selection-background-color: #1e2c45;
    selection-color: #ffffff;
    font-size: 12px;
}
QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #131b2c;
}
QTableWidget::item:hover {
    background-color: rgba(255, 255, 255, 0.02);
}
QHeaderView::section {
    background-color: #070b14;
    color: #94a3b8;
    padding: 9px 8px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    border: none;
    border-bottom: 1px solid #1e293b;
    border-right: 1px solid #111827;
}

/* PlainTextEdit (Terminal) */
QPlainTextEdit {
    background-color: #040711;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 10px;
    color: #e2e8f0;
    font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
    font-size: 12px;
    line-height: 1.5;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #1e293b;
    border-radius: 10px;
    background-color: #0b1019;
    top: -1px;
}
QTabBar::tab {
    background-color: #0c121e;
    border: 1px solid #1e293b;
    color: #94a3b8;
    padding: 8px 16px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
    font-size: 12px;
}
QTabBar::tab:selected {
    background-color: #162032;
    color: #38bdf8;
    border-bottom: 2px solid #38bdf8;
}
QTabBar::tab:hover:!selected {
    background-color: #111827;
    color: #ffffff;
}

/* Dialog */
QDialog {
    background-color: #0c121e;
    border: 1px solid #1e293b;
    border-radius: 14px;
}

/* Status Bar */
QStatusBar {
    background-color: #060911;
    border-top: 1px solid #1e293b;
    color: #64748b;
    font-size: 11px;
}
"""
