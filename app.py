#!/usr/bin/env python3
"""VortexDBA - 100% Native PyQt6 Desktop Application Launcher."""

import sys
from pathlib import Path

# Add src to sys.path
SRC_DIR = Path(__file__).parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from gui.main_window import MainWindow


def main():
    """Start the native desktop application."""
    # Set Windows AppUserModelID for taskbar icon
    try:
        import ctypes
        myappid = "vortexdba.enterprise.gui.v2"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("VortexDBA")
    app.setOrganizationName("VortexDBA")

    logo_path = Path(__file__).parent / "logo.svg"
    if logo_path.exists():
        app.setWindowIcon(QIcon(str(logo_path)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())



if __name__ == "__main__":
    main()
