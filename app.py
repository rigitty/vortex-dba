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

    from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
    from gui.widgets.splash_screen import SplashScreen

    window = MainWindow()
    window.setWindowOpacity(0.0)

    def show_window_smooth():
        window.center_on_screen()
        window.show()
        anim = QPropertyAnimation(window, b"windowOpacity")

        anim.setDuration(700)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        window._fade_in_anim = anim  # Prevent garbage collection
        anim.start()

    splash = SplashScreen(logo_path=logo_path)
    splash.finished.connect(show_window_smooth)
    splash.show()

    sys.exit(app.exec())



if __name__ == "__main__":
    main()

