"""Seamless Borderless Splash Screen for VortexDBA."""
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QIcon

try:
    from src.i18n import t
except ImportError:
    from i18n import t



class SplashScreen(QWidget):
    """Completely borderless, frameless minimal splash screen with smooth fade transitions."""
    finished = pyqtSignal()

    def __init__(self, logo_path: Path = None):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(480, 290)
        self.setStyleSheet("background-color: #000000; border: none;")
        self.center_on_screen()

        self._elapsed_ms = 0
        self._is_cancelled = False
        self.TOTAL_DURATION_MS = 3000

        # Close [✖] Button in Top Right
        self.btn_close = QPushButton("✖", self)
        self.btn_close.setGeometry(446, 10, 24, 24)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #64748b;
                font-size: 13px;
                font-weight: 700;
                padding: 0;
            }
            QPushButton:hover {
                color: #f43f5e;
                background: rgba(244, 63, 94, 0.15);
                border-radius: 2px;
            }
        """)
        self.btn_close.clicked.connect(self.cancel_and_quit)
        self.btn_close.show()
        self.btn_close.raise_()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Logo (Completely seamless icon, zero boxes or borders)
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent; border: none; padding: 0px;")
        if logo_path and logo_path.exists():
            pix = QIcon(str(logo_path)).pixmap(72, 72)
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("⚡")
            logo_lbl.setStyleSheet("font-size: 56px; color: #06b6d4; background: transparent; border: none;")
        layout.addWidget(logo_lbl)

        # 2. Typography: VORTEX DBA
        brand_lbl = QLabel("VORTEX DBA")
        brand_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_lbl.setStyleSheet("font-size: 24px; font-weight: 900; color: #ffffff; letter-spacing: 3px; font-family: 'JetBrains Mono', 'Segoe UI', monospace; background: transparent; border: none;")
        layout.addWidget(brand_lbl)

        layout.addSpacing(4)

        # 3. Moving Neon Progress Bar (No border box)
        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedHeight(4)
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setStyleSheet("""
            QProgressBar {
                background-color: #10101a;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:0.5 #06b6d4, stop:1 #38bdf8);
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.prog_bar)

        # 4. Status Text (Loading Steps)
        self.lbl_status = QLabel("● Sistem bileşenleri başlatılıyor...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 11px; font-weight: 600; color: #9494a8; font-family: 'JetBrains Mono', monospace; background: transparent; border: none;")
        layout.addWidget(self.lbl_status)

        # Timer for 3-Second Sequence
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

    def _on_tick(self):
        self._elapsed_ms += 25
        pct = min(100, int((self._elapsed_ms / self.TOTAL_DURATION_MS) * 100))
        self.prog_bar.setValue(pct)

        if self._elapsed_ms < 1000:
            self.lbl_status.setText(t("splash.step1"))
        elif self._elapsed_ms < 2000:
            self.lbl_status.setText(t("splash.step2"))
        elif self._elapsed_ms < 2700:
            self.lbl_status.setText(t("splash.step3"))
        else:
            self.lbl_status.setText(t("splash.ready"))


        if self._elapsed_ms >= self.TOTAL_DURATION_MS:
            self.timer.stop()
            self._fade_out_and_finish()

    def center_on_screen(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)

    def cancel_and_quit(self):
        """Immediately abort application startup and terminate process."""
        self._is_cancelled = True
        if hasattr(self, "timer"):
            self.timer.stop()
        if hasattr(self, "anim"):
            self.anim.stop()
        self.close()
        app = QApplication.instance()
        if app:
            app.quit()
        sys.exit(0)

    def _fade_out_and_finish(self):
        if self._is_cancelled:
            return
        # Smooth fade-out from 1.0 down to 0.0
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(700)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.anim.finished.connect(self._on_fade_finished)
        self.anim.start()

    def _on_fade_finished(self):
        if not self._is_cancelled:
            self.finished.emit()
        self.close()


