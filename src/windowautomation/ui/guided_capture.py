from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from windowautomation import capture


class CaptureCanvas(QWidget):
    pointSelected = Signal(int, int)

    def __init__(self, image: np.ndarray, parent=None):
        super().__init__(parent)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width = rgb.shape[:2]
        self._pixmap = QPixmap.fromImage(QImage(rgb.data, width, height, width * 3, QImage.Format.Format_RGB888).copy())
        self._click = None
        self.setMinimumSize(640, 360)

    def _scale(self) -> float:
        return min(self.width() / self._pixmap.width(), self.height() / self._pixmap.height())

    def _image_rect(self) -> QRect:
        scale = self._scale()
        size = self._pixmap.size() * scale
        rect = QRect(QPoint(0, 0), size)
        rect.moveCenter(self.rect().center())
        return rect

    def _image_point(self, point: QPoint) -> QPoint | None:
        rect = self._image_rect()
        if not rect.contains(point):
            return None
        scale = self._scale()
        return QPoint(round((point.x() - rect.x()) / scale), round((point.y() - rect.y()) / scale))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1f2937"))
        rect = self._image_rect()
        painter.drawPixmap(rect, self._pixmap)
        if self._click is not None:
            scale = self._scale()
            marker = QPoint(rect.x() + round(self._click.x() * scale), rect.y() + round(self._click.y() * scale))
            painter.setPen(Qt.GlobalColor.red)
            painter.drawLine(marker.x() - 12, marker.y(), marker.x() + 12, marker.y())
            painter.drawLine(marker.x(), marker.y() - 12, marker.x(), marker.y() + 12)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        point = self._image_point(event.position().toPoint())
        if point is None:
            return
        self._click = point
        self.pointSelected.emit(point.x(), point.y())
        self.update()


class GuidedCaptureDialog(QDialog):
    def __init__(self, screen, screens, template_dir: str, delay_s: float = 3.0, parent=None):
        super().__init__(parent)
        self.screen = screen
        self.screens = screens
        self.template_dir = Path(template_dir).expanduser()
        self.delay_s = delay_s
        self.setWindowTitle("Guided capture")
        self.setModal(True)
        self.resize(420, 200)
        self.instructions = QLabel(
            f"Move your mouse to the target on the selected monitor, then press Start capture.\n"
            f"The app will hide and the screenshot will be taken automatically after {delay_s:g} seconds."
        )
        self.instructions.setWordWrap(True)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Action name")
        self.canvas = None
        self._image = None
        self._click = None
        self.start_button = QPushButton("Start capture")
        self.start_button.clicked.connect(self._begin)
        self.cancel_button = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.cancel_button.rejected.connect(self.reject)
        self.capture_button = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.capture_button.button(QDialogButtonBox.StandardButton.Ok).setText("Save action")
        self.capture_button.accepted.connect(self.save_action)
        # Cancel/Save action only make sense once a screenshot exists to click on;
        # keep the pre-capture screen down to just the Start button.
        self.cancel_button.hide()
        self.capture_button.hide()
        form = QFormLayout()
        self.name_label = QLabel("Action name")
        form.addRow(self.name_label, self.name)
        self.name_label.hide()
        self.name.hide()
        layout = QVBoxLayout(self)
        layout.addWidget(self.instructions)
        layout.addLayout(form)
        layout.addWidget(self.start_button)
        layout.addWidget(self.cancel_button)
        layout.addWidget(self.capture_button)
        self.capture_timer = QTimer(self)
        self.capture_timer.setSingleShot(True)
        self.capture_timer.timeout.connect(self._capture)
        self.setStyleSheet("""
            QDialog { background: #f4f6f8; }
            QLabel { color: #344054; }
            QLineEdit { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 5px; padding: 6px; color: #1f2937; }
            QPushButton { background: #ffffff; border: 1px solid #94a3b8; border-radius: 5px; padding: 7px 10px; color: #1f2937; }
            QPushButton:hover { background: #e0f2fe; }
        """)

    def _virtual_rect(self) -> QRect:
        virtual = self.screens[0].geometry()
        for current in self.screens[1:]:
            virtual = virtual.united(current.geometry())
        return virtual

    def _begin(self) -> None:
        self.start_button.setEnabled(False)
        # Hide every window belonging to this app so nothing of it can appear in the
        # screenshot, then wait out the delay before capturing. This dialog is shown
        # via show() with setModal(True) rather than exec(), specifically so hide()
        # here doesn't tear down a nested modal event loop (QDialog.exec() would abort
        # immediately on hide()). Minimize/restore isn't used because Wayland compositors
        # can refuse to restore a minimized window without direct user input, which can
        # leave it stuck hidden.
        if self.parent():
            self.parent().hide()
        self.hide()
        self.capture_timer.start(int(self.delay_s * 1000))

    def reject(self) -> None:
        self.capture_timer.stop()
        if self.parent():
            self.parent().show()
        super().reject()

    def _capture(self) -> None:
        try:
            screen_geometry = self.screen.geometry()
            self._image = capture.capture_monitor(
                screen_geometry.getRect(), self._virtual_rect().getRect()
            )
            self.canvas = CaptureCanvas(self._image, self)
            self.canvas.pointSelected.connect(self._set_click)
            self.layout().insertWidget(2, self.canvas)
            self.instructions.setText("Click the exact point that should be clicked, then enter a name and press Save.")
            self.start_button.hide()
            self.name_label.show()
            self.name.show()
            self.cancel_button.show()
            self.capture_button.show()
            self.resize(900, 650)
        except Exception as exc:
            # Any failure here must still restore visibility, or the app stays hidden forever.
            if self.parent():
                self.parent().show()
            self.show()
            QMessageBox.critical(self, "Capture failed", str(exc))
            self.reject()
            return
        if self.parent():
            self.parent().show()
        self.show()

    def _set_click(self, x: int, y: int) -> None:
        self._click = (x, y)
        self.instructions.setText(f"Click point: ({x}, {y}). Enter a name and press Save.")

    def save_action(self) -> None:
        if not self._click or not self.name.text().strip():
            QMessageBox.warning(self, "Guided capture", "Click the target point and enter an action name.")
            return
        self.template_dir.mkdir(parents=True, exist_ok=True)
        name = self.name.text().strip()
        path = self.template_dir / f"{name}.png"
        cv2.imwrite(str(path), self._image)
        self.template_path = str(path)
        self.click_offset = self._click
        self.accept()
