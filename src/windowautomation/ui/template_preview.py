from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QLabel


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


class TemplatePreview(QLabel):
    pointSelected = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(260, 180)
        self.setText("Select a template to preview it")
        self._pixmap = QPixmap()
        self._image_rect = None
        self._path = None

    def set_preview(self, path: str | None, visible: bool) -> None:
        self._path = path
        if not visible or not path:
            self._pixmap = QPixmap()
            self._image_rect = None
            self.setPixmap(QPixmap())
            self.setText("Preview hidden")
            return
        pixmap = QPixmap(path)
        self._pixmap = pixmap
        if pixmap.isNull():
            self._image_rect = None
            self.setText("Unable to preview image")
            return
        scaled = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._image_rect = scaled.rect()
        self._image_rect.moveCenter(self.rect().center())
        self.setPixmap(scaled)
        self.setText("")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._path:
            self.set_preview(self._path, True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._pixmap.isNull() or self._image_rect is None:
            return super().mousePressEvent(event)
        if not self._image_rect.contains(event.position().toPoint()):
            return
        point = event.position().toPoint() - self._image_rect.topLeft()
        scale_x = self._pixmap.width() / self._image_rect.width()
        scale_y = self._pixmap.height() / self._image_rect.height()
        image_x = round(point.x() * scale_x)
        image_y = round(point.y() * scale_y)
        self.pointSelected.emit(image_x, image_y)

def import_templates(paths: list[str], target_dir: str) -> list[str]:
    destination = Path(target_dir).expanduser()
    destination.mkdir(parents=True, exist_ok=True)
    imported = []
    for source in paths:
        source_path = Path(source)
        target = destination / source_path.name
        if source_path.resolve() != target.resolve():
            shutil.copy2(source_path, target)
        imported.append(str(target))
    return imported
