"""Custom Animated Dark/Light Theme Toggle Switch matching Uiverse.io Madflows design."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, pyqtProperty, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath


class ThemeToggleSwitch(QWidget):
    """Futuristic animated theme toggle switch with crescent moon / sun states."""
    toggled = pyqtSignal(bool)  # True = Light theme, False = Dark theme

    def __init__(self, is_light: bool = False, parent: QWidget = None):
        super().__init__(parent)
        self._is_light = is_light
        self._offset = 1.0 if is_light else 0.0

        self.setFixedSize(54, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Koyu / Aydınlık Tema Değiştir")

        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(280)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    @pyqtProperty(float)
    def offset(self) -> float:
        return self._offset

    @offset.setter
    def offset(self, val: float):
        self._offset = val
        self.update()

    def is_light_theme(self) -> bool:
        return self._is_light

    def set_light_theme(self, is_light: bool, animate: bool = True):
        if self._is_light != is_light:
            self._is_light = is_light
            target = 1.0 if is_light else 0.0
            if animate:
                self._anim.stop()
                self._anim.setStartValue(self._offset)
                self._anim.setEndValue(target)
                self._anim.start()
            else:
                self.offset = target

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_light = not self._is_light
            target = 1.0 if self._is_light else 0.0
            self._anim.stop()
            self._anim.setStartValue(self._offset)
            self._anim.setEndValue(target)
            self._anim.start()
            self.toggled.emit(self._is_light)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        r = h / 2.0

        # Colors from Uiverse.io spec
        dark_col = QColor("#28292c")
        light_col = QColor("#d8dbe0")

        # Interpolate track background
        # 0.0 -> #28292c, 1.0 -> #d8dbe0
        t = self._offset
        track_r = int(dark_col.red() + (light_col.red() - dark_col.red()) * t)
        track_g = int(dark_col.green() + (light_col.green() - dark_col.green()) * t)
        track_b = int(dark_col.blue() + (light_col.blue() - dark_col.blue()) * t)
        track_color = QColor(track_r, track_g, track_b)

        # Draw pill track
        p.setPen(QPen(QColor(40, 41, 44, 200) if t < 0.5 else QColor(180, 185, 195), 1.5))
        p.setBrush(QBrush(track_color))
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), r - 1, r - 1)

        # Knob geometry
        knob_d = h - 8.0
        knob_r = knob_d / 2.0
        x_travel = w - knob_d - 8.0
        knob_x = 4.0 + t * x_travel
        knob_y = 4.0
        center_x = knob_x + knob_r
        center_y = knob_y + knob_r

        if t < 0.5:
            # Moon Mode: Dark knob with crescent moon
            # 1. Base dark circle
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(dark_col))
            p.drawEllipse(QRectF(knob_x, knob_y, knob_d, knob_d))

            # 2. Crescent moon: Light circle minus dark cutout
            moon_path = QPainterPath()
            moon_path.addEllipse(QPointF(center_x, center_y), knob_r - 1.5, knob_r - 1.5)

            cutout_path = QPainterPath()
            cutout_path.addEllipse(QPointF(center_x - 3.5, center_y - 2.0), knob_r - 1.2, knob_r - 1.2)

            crescent = moon_path.subtracted(cutout_path)
            p.setBrush(QBrush(light_col))
            p.drawPath(crescent)
        else:
            # Sun / Light Mode: Solid dark knob (#28292c) matching specification
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(dark_col))
            p.drawEllipse(QRectF(knob_x, knob_y, knob_d, knob_d))

        p.end()
