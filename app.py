import os
import sys
from pathlib import Path

# Add src and root to sys.path
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
    EXE_DIR = Path(sys.executable).parent.resolve()
else:
    BASE_DIR = Path(__file__).parent.resolve()
    EXE_DIR = BASE_DIR

SRC_DIR = BASE_DIR / "src"

for p in [str(SRC_DIR), str(BASE_DIR), str(EXE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

try:
    from gui.main_window import MainWindow
except ImportError:
    from src.gui.main_window import MainWindow


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

    app.setQuitOnLastWindowClosed(False)

    logo_path = BASE_DIR / "logo.svg"
    if not logo_path.exists():
        logo_path = EXE_DIR / "logo.svg"
    if not logo_path.exists():
        logo_path = Path.cwd() / "logo.svg"

    if logo_path.exists():
        app.setWindowIcon(QIcon(str(logo_path)))

    from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
    try:
        from gui.widgets.splash_screen import SplashScreen
    except ImportError:
        from src.gui.widgets.splash_screen import SplashScreen

    window = MainWindow()

    def show_window_smooth():
        app.setQuitOnLastWindowClosed(True)
        window.center_on_screen()
        window.show()
        window.raise_()
        window.activateWindow()

        try:
            anim = QPropertyAnimation(window, b"windowOpacity")
            anim.setDuration(400)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            window._fade_in_anim = anim  # Prevent garbage collection
            anim.start()
        except Exception:
            window.setWindowOpacity(1.0)

    splash = SplashScreen(logo_path=logo_path)
    splash.finished.connect(show_window_smooth)
    splash.show()


    sys.exit(app.exec())




if __name__ == "__main__":
    main()

