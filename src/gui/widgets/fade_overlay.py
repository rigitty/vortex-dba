"""Lightweight, 60fps non-blocking Crossfade Overlay for smooth theme switching."""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QPixmap


class ThemeFadeOverlay(QWidget):
    """Smooth crossfade overlay widget that fades out a pre-switch snapshot over the new theme."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._pixmap: QPixmap = None
        self._opacity: float = 1.0
        self.hide()

    def get_opacity(self) -> float:
        return self._opacity

    def set_opacity(self, val: float):
        self._opacity = max(0.0, min(1.0, val))
        self.update()

    opacity = pyqtProperty(float, get_opacity, set_opacity)

    def start_crossfade(self, pixmap: QPixmap, duration_ms: int = 220):
        """Displays pixmap snapshot and smoothly fades out over duration_ms."""
        if not pixmap or pixmap.isNull():
            return
        self._pixmap = pixmap
        self._opacity = 1.0
        if self.parent():
            self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        self.raise_()
        self.show()

        anim = QPropertyAnimation(self, b"opacity", self)
        anim.setDuration(duration_ms)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.finished.connect(self.hide)
        anim.start()
        self._anim = anim

    def paintEvent(self, event):
        if self._pixmap and not self._pixmap.isNull() and self._opacity > 0.0:
            painter = QPainter(self)
            painter.setOpacity(self._opacity)
            painter.drawPixmap(0, 0, self._pixmap)
            painter.end()
