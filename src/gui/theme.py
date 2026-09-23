"""Modern Enterprise Dark and Light Theme Stylesheets for VortexDBA."""

def get_theme_color(is_light: bool, key: str) -> str:
    """Returns exact hex color for the given token based on active theme."""
    palette = {
        # Text colors
        "text_primary": "#0f172a" if is_light else "#f8fafc",
        "text_secondary": "#1e293b" if is_light else "#cbd5e1",
        "text_muted": "#475569" if is_light else "#9494a8",
        "text_code": "#0369a1" if is_light else "#93c5fd",
        "text_dim": "#64748b" if is_light else "#525266",
        
        # Accents
        "accent_primary": "#0284c7" if is_light else "#38bdf8",
        "accent_success": "#047857" if is_light else "#10b981",
        "accent_danger": "#be123c" if is_light else "#f43f5e",
        "accent_warning": "#b45309" if is_light else "#f59e0b",
        "accent_cyan": "#0369a1" if is_light else "#06b6d4",
        "accent_blue": "#1d4ed8" if is_light else "#38bdf8",

        # Panels, Cards & Widgets
        "bg_main": "#f8fafc" if is_light else "#000000",
        "bg_card": "#ffffff" if is_light else "#07070a",
        "bg_header": "#ffffff" if is_light else "#07070a",
        "bg_subtle": "#f1f5f9" if is_light else "#040407",
        "bg_tertiary": "#e2e8f0" if is_light else "#111118",
        "bg_hover": "#cbd5e1" if is_light else "#1e1e2d",
        "border_card": "#cbd5e1" if is_light else "#1a1a24",
        "border_subtle": "#cbd5e1" if is_light else "#111118",
        "border_color": "#cbd5e1" if is_light else "#2a2a3c",

        # Badges
        "badge_online_bg": "#d1fae5" if is_light else "#041a12",
        "badge_online_text": "#065f46" if is_light else "#10b981",
        "badge_online_border": "#059669" if is_light else "#10b981",

        "badge_offline_bg": "#ffe4e6" if is_light else "#1f060c",
        "badge_offline_text": "#9f1239" if is_light else "#f43f5e",
        "badge_offline_border": "#e11d48" if is_light else "#f43f5e",

        "badge_engine_on_bg": "#d1fae5" if is_light else "#041a12",
        "badge_engine_on_text": "#065f46" if is_light else "#10b981",
        "badge_engine_on_border": "#059669" if is_light else "#10b981",

        "badge_engine_off_bg": "#f1f5f9" if is_light else "#181822",
        "badge_engine_off_text": "#475569" if is_light else "#9494a8",
        "badge_engine_off_border": "#94a3b8" if is_light else "#3e3e56",

        # Banner & Strip
        "strip_bg": "#f1f5f9" if is_light else "#040407",
        "strip_text": "#0f172a" if is_light else "#cbd5e1",
        "strip_border": "#cbd5e1" if is_light else "#1a1a24",

        "rec_bg": "#ecfeff" if is_light else "#03141c",
        "rec_border": "#0891b2" if is_light else "#06b6d4",
        "rec_text": "#0e7490" if is_light else "#6ee7b7",
    }
    return palette.get(key, "#0f172a" if is_light else "#f8fafc")


DARK_THEME_QSS = """
/* Global Application Styles - Pure Cyber Dark */
QWidget {
    background-color: #000000;
    color: #e2e8f0;
    font-family: "JetBrains Mono", "Segoe UI", "Inter", -apple-system, sans-serif;
    font-size: 11.5px;
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
}

QMainWindow {
    background-color: #000000;
}

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

/* Solid Cards & Frames */
QFrame.card-panel, QFrame[class="card-panel"] {
    background-color: #07070a;
    border: 1px solid #1a1a24;
    border-radius: 2px;
}

QFrame.header-panel, QFrame[class="header-panel"] {
    background-color: #07070a;
    border-bottom: 1px solid #1a1a24;
}

/* Standard Buttons */
QPushButton {
    background-color: #0c0c14;
    border: 1px solid #2a2a3c;
    color: #e2e8f0;
    border-radius: 3px;
    padding: 7px 14px;
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

/* Primary Blue Action Button */
QPushButton[class="btn-primary"], QPushButton.btn-primary {
    background-color: #1d4ed8;
    border: 1px solid #3b82f6;
    color: #ffffff;
    font-weight: 800;
    font-size: 11.5px;
    padding: 7px 16px;
    border-radius: 3px;
}
QPushButton[class="btn-primary"]:hover, QPushButton.btn-primary:hover {
    background-color: #2563eb;
    border: 1px solid #93c5fd;
    color: #ffffff;
}
QPushButton[class="btn-primary"]:pressed, QPushButton.btn-primary:pressed {
    background-color: #1e40af;
    border: 1px solid #bfdbfe;
}

/* Success Green Action Button */
QPushButton[class="btn-success"], QPushButton.btn-success {
    background-color: #065f46;
    border: 1px solid #10b981;
    color: #ffffff;
    font-weight: 800;
    font-size: 11.5px;
    padding: 7px 16px;
    border-radius: 3px;
}
QPushButton[class="btn-success"]:hover, QPushButton.btn-success:hover {
    background-color: #047857;
    border: 1px solid #6ee7b7;
    color: #ffffff;
}
QPushButton[class="btn-success"]:pressed, QPushButton.btn-success:pressed {
    background-color: #064e3b;
    border: 1px solid #a7f3d0;
}

/* Warning Amber Action Button */
QPushButton[class="btn-warning"], QPushButton.btn-warning {
    background-color: #854d0e;
    border: 1px solid #f59e0b;
    color: #ffffff;
    font-weight: 800;
    font-size: 11.5px;
    padding: 7px 16px;
    border-radius: 3px;
}
QPushButton[class="btn-warning"]:hover, QPushButton.btn-warning:hover {
    background-color: #a16207;
    border: 1px solid #fde68a;
    color: #ffffff;
}
QPushButton[class="btn-warning"]:pressed, QPushButton.btn-warning:pressed {
    background-color: #713f12;
    border: 1px solid #fef3c7;
}

/* Danger Red Button */
QPushButton[class="btn-danger"], QPushButton.btn-danger {
    background-color: #881337;
    border: 1px solid #f43f5e;
    color: #ffffff;
    font-weight: 800;
    font-size: 11.5px;
    padding: 7px 16px;
    border-radius: 3px;
}
QPushButton[class="btn-danger"]:hover, QPushButton.btn-danger:hover {
    background-color: #9f1239;
    border: 1px solid #fecdd3;
    color: #ffffff;
}
QPushButton[class="btn-danger"]:pressed, QPushButton.btn-danger:pressed {
    background-color: #4c0519;
    border: 1px solid #ffe4e6;
}

/* Top Nav Tab Button - Contiguous Segmented Cyber Tabs (Uniform Width) */
QPushButton[class="nav-tab-btn"], QPushButton.nav-tab-btn {
    background-color: #090910;
    border: none;
    border-right: 1px solid #1a1a28;
    color: #8b8b9e;
    padding: 0px 0px;
    min-width: 105px;
    max-width: 105px;
    height: 42px;
    text-align: center;
    font-weight: 800;
    font-size: 12px;
    font-family: "JetBrains Mono", monospace;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-radius: 0px;
}
QPushButton[class="nav-tab-btn"]:hover, QPushButton.nav-tab-btn:hover {
    background-color: #141424;
    color: #ffffff;
}
QPushButton[class="nav-tab-btn"]:checked, QPushButton.nav-tab-btn:checked {
    background-color: #0e2238;
    color: #38bdf8;
    border-bottom: 3px solid #06b6d4;
    font-weight: 800;
}

/* Table Cell Compact Action Buttons (Guarantees Visible Text) */
QTableWidget QPushButton, 
QTableWidget QPushButton[class="btn-success"], 
QTableWidget QPushButton[class="btn-danger"], 
QTableWidget QPushButton[class="btn-warning"], 
QTableWidget QPushButton[class="btn-primary"] {
    padding: 3px 6px;
    font-size: 11px;
    font-weight: 800;
    min-height: 24px;
    max-height: 28px;
    border-radius: 2px;
}

/* Input Fields */
QLineEdit, QSpinBox {
    background-color: #020204;
    border: 1px solid #1a1a24;
    border-radius: 2px;
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
QLabel.label-muted, QLabel[class="label-muted"] {
    color: #64748b;
    font-size: 10.5px;
}
QLabel.label-title, QLabel[class="label-title"] {
    font-size: 13px;
    font-weight: 700;
    color: #ffffff;
    font-family: "JetBrains Mono", monospace;
}

/* Table Widget */
QTableWidget {
    background-color: #020204;
    border: 1px solid #1a1a24;
    border-radius: 2px;
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
    border-radius: 2px;
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

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #1a1a24;
    background-color: #000000;
    border-radius: 2px;
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


LIGHT_THEME_QSS = """
/* Global Application Styles - High Contrast Modern Clean Light Mode */
QWidget {
    background-color: #f8fafc;
    color: #0f172a;
    font-family: "JetBrains Mono", "Segoe UI", "Inter", -apple-system, sans-serif;
    font-size: 11.5px;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
}

QMainWindow {
    background-color: #f8fafc;
}

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
    background: #f1f5f9;
    width: 6px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 20px;
    border-radius: 0px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #f1f5f9;
    height: 6px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #cbd5e1;
    min-width: 20px;
    border-radius: 0px;
}
QScrollBar::handle:horizontal:hover {
    background: #94a3b8;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Solid Cards & Frames */
QFrame.card-panel, QFrame[class="card-panel"] {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 2px;
}

QFrame.header-panel, QFrame[class="header-panel"] {
    background-color: #ffffff;
    border-bottom: 2px solid #cbd5e1;
}

/* Standard Buttons (Non-colored) */
QPushButton {
    background-color: #e2e8f0;
    border: 1px solid #94a3b8;
    color: #0f172a;
    border-radius: 3px;
    padding: 7px 14px;
    font-weight: 700;
    font-size: 11.5px;
    font-family: "JetBrains Mono", monospace;
    text-transform: uppercase;
}
QPushButton:hover {
    background-color: #cbd5e1;
    border-color: #64748b;
    color: #000000;
}
QPushButton:pressed {
    background-color: #94a3b8;
    border-color: #0284c7;
}
QPushButton:disabled {
    background-color: #f1f5f9;
    border-color: #e2e8f0;
    color: #94a3b8;
}

/* Primary Blue Action Button */
QPushButton[class="btn-primary"], QPushButton.btn-primary {
    background-color: #0284c7;
    border: 1px solid #0369a1;
    color: #ffffff;
    font-weight: 800;
    font-size: 11.5px;
    padding: 7px 16px;
    border-radius: 3px;
}
QPushButton[class="btn-primary"]:hover, QPushButton.btn-primary:hover {
    background-color: #0369a1;
    border: 1px solid #075985;
    color: #ffffff;
}
QPushButton[class="btn-primary"]:pressed, QPushButton.btn-primary:pressed {
    background-color: #0c4a6e;
    border: 1px solid #0369a1;
}

/* Success Green Action Button */
QPushButton[class="btn-success"], QPushButton.btn-success {
    background-color: #059669;
    border: 1px solid #047857;
    color: #ffffff;
    font-weight: 800;
    font-size: 11.5px;
    padding: 7px 16px;
    border-radius: 3px;
}
QPushButton[class="btn-success"]:hover, QPushButton.btn-success:hover {
    background-color: #047857;
    border: 1px solid #065f46;
    color: #ffffff;
}
QPushButton[class="btn-success"]:pressed, QPushButton.btn-success:pressed {
    background-color: #064e3b;
    border: 1px solid #047857;
}

/* Warning Amber Action Button */
QPushButton[class="btn-warning"], QPushButton.btn-warning {
    background-color: #d97706;
    border: 1px solid #b45309;
    color: #ffffff;
    font-weight: 800;
    font-size: 11.5px;
    padding: 7px 16px;
    border-radius: 3px;
}
QPushButton[class="btn-warning"]:hover, QPushButton.btn-warning:hover {
    background-color: #b45309;
    border: 1px solid #92400e;
    color: #ffffff;
}
QPushButton[class="btn-warning"]:pressed, QPushButton.btn-warning:pressed {
    background-color: #78350f;
    border: 1px solid #b45309;
}

/* Danger Red Button */
QPushButton[class="btn-danger"], QPushButton.btn-danger {
    background-color: #e11d48;
    border: 1px solid #be123c;
    color: #ffffff;
    font-weight: 800;
    font-size: 11.5px;
    padding: 7px 16px;
    border-radius: 3px;
}
QPushButton[class="btn-danger"]:hover, QPushButton.btn-danger:hover {
    background-color: #be123c;
    border: 1px solid #9f1239;
    color: #ffffff;
}
QPushButton[class="btn-danger"]:pressed, QPushButton.btn-danger:pressed {
    background-color: #881337;
    border: 1px solid #be123c;
}

/* Top Nav Tab Button - Contiguous Segmented Light Tabs (Uniform Width) */
QPushButton[class="nav-tab-btn"], QPushButton.nav-tab-btn {
    background-color: #e2e8f0;
    border: none;
    border-right: 1px solid #cbd5e1;
    color: #334155;
    padding: 0px 0px;
    min-width: 105px;
    max-width: 105px;
    height: 42px;
    text-align: center;
    font-weight: 800;
    font-size: 12px;
    font-family: "JetBrains Mono", monospace;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-radius: 0px;
}
QPushButton[class="nav-tab-btn"]:hover, QPushButton.nav-tab-btn:hover {
    background-color: #cbd5e1;
    color: #0f172a;
}
QPushButton[class="nav-tab-btn"]:checked, QPushButton.nav-tab-btn:checked {
    background-color: #0284c7;
    color: #ffffff;
    border-bottom: 3px solid #0369a1;
    font-weight: 800;
}

/* Table Cell Compact Action Buttons (Guarantees Visible Text) */
QTableWidget QPushButton, 
QTableWidget QPushButton[class="btn-success"], 
QTableWidget QPushButton[class="btn-danger"], 
QTableWidget QPushButton[class="btn-warning"], 
QTableWidget QPushButton[class="btn-primary"] {
    padding: 3px 6px;
    font-size: 11px;
    font-weight: 800;
    min-height: 24px;
    max-height: 28px;
    border-radius: 2px;
}

/* Input Fields */
QLineEdit, QSpinBox {
    background-color: #ffffff;
    border: 1px solid #94a3b8;
    border-radius: 2px;
    padding: 6px 10px;
    color: #0f172a;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #0284c7;
    background-color: #ffffff;
}

/* Labels */
QLabel {
    background-color: transparent;
    color: #0f172a;
}
QLabel.label-muted, QLabel[class="label-muted"] {
    color: #64748b;
    font-size: 10.5px;
}
QLabel.label-title, QLabel[class="label-title"] {
    font-size: 13px;
    font-weight: 700;
    color: #0f172a;
    font-family: "JetBrains Mono", monospace;
}

/* Table Widget - High Contrast Crisp Grid */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 2px;
    gridline-color: #e2e8f0;
    color: #0f172a;
    selection-background-color: #e0f2fe;
    selection-color: #0369a1;
    font-size: 11.5px;
    font-family: "JetBrains Mono", "Segoe UI", sans-serif;
}
QTableWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #f1f5f9;
}
QTableWidget::item:hover {
    background-color: #f8fafc;
}
QHeaderView::section {
    background-color: #e2e8f0;
    color: #0f172a;
    padding: 8px 10px;
    font-size: 10.5px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: none;
    border-bottom: 2px solid #cbd5e1;
    border-right: 1px solid #cbd5e1;
    font-family: "JetBrains Mono", monospace;
}

/* PlainTextEdit (SQL Editor & Terminal) */
QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 2px;
    padding: 10px 12px;
    color: #0f172a;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 11.5px;
    line-height: 1.45;
}
QPlainTextEdit:focus {
    border-color: #0284c7;
    background-color: #ffffff;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #cbd5e1;
    background-color: #ffffff;
    border-radius: 2px;
}
QTabBar::tab {
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
    color: #64748b;
    padding: 7px 16px;
    font-weight: 700;
    font-size: 11px;
    font-family: "JetBrains Mono", monospace;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0f172a;
    border-bottom: 2px solid #0284c7;
}
"""