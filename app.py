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
    app = QApplication(sys.argv)
    app.setApplicationName("VortexDBA")
    app.setOrganizationName("VortexDBA")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
