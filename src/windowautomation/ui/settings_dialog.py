from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QDoubleSpinBox

from windowautomation.config import Config


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.template_dir = QLineEdit(config.template_dir)
        self.socket_path = QLineEdit(config.ydotool_socket)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.0, 1.0)
        self.threshold.setSingleStep(0.01)
        self.threshold.setValue(config.default_threshold)
        self.guided_capture_delay = QDoubleSpinBox()
        self.guided_capture_delay.setRange(1.0, 30.0)
        self.guided_capture_delay.setSingleStep(0.5)
        self.guided_capture_delay.setSuffix(" s")
        self.guided_capture_delay.setValue(config.guided_capture_delay_s)

        form = QFormLayout(self)
        form.addRow("Template folder", self.template_dir)
        form.addRow("ydotool socket", self.socket_path)
        form.addRow("Default threshold", self.threshold)
        form.addRow("Guided capture delay", self.guided_capture_delay)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def apply_to(self, config: Config) -> None:
        config.template_dir = self.template_dir.text().strip()
        config.ydotool_socket = self.socket_path.text().strip()
        config.guided_capture_delay_s = self.guided_capture_delay.value()
        config.default_threshold = self.threshold.value()
