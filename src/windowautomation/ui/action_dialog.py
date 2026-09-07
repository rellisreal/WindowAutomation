from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLineEdit, QSpinBox

from windowautomation.config import Action, Config


class ActionDialog(QDialog):
    def __init__(self, config: Config, action: Action | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create action" if action is None else "Edit action")
        self.name = QLineEdit(action.name if action else "")
        self.template = QComboBox()
        self.template.addItems(self._template_names(config))
        if action:
            index = self.template.findText(action.template_path)
            if index >= 0:
                self.template.setCurrentIndex(index)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.0, 1.0)
        self.threshold.setSingleStep(0.01)
        self.threshold.setValue(action.threshold if action else config.default_threshold)
        self.interval = QDoubleSpinBox()
        self.interval.setRange(0.1, 60.0)
        self.interval.setSuffix(" s")
        self.interval.setValue(action.poll_interval_s if action else 1.0)
        self.offset_x = QSpinBox()
        self.offset_x.setRange(-10000, 10000)
        self.offset_x.setValue(action.click_offset_x if action else 0)
        self.offset_y = QSpinBox()
        self.offset_y.setRange(-10000, 10000)
        self.offset_y.setValue(action.click_offset_y if action else 0)

        form = QFormLayout(self)
        form.addRow("Action name", self.name)
        form.addRow("Template", self.template)
        form.addRow("Match threshold", self.threshold)
        form.addRow("Poll interval", self.interval)
        form.addRow("Click offset X", self.offset_x)
        form.addRow("Click offset Y", self.offset_y)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    @staticmethod
    def _template_names(config: Config) -> list[str]:
        from pathlib import Path
        from windowautomation.ui.template_preview import IMAGE_SUFFIXES
        directory = Path(config.template_dir).expanduser()
        if not directory.exists():
            return []
        return [str(path) for path in sorted(directory.iterdir()) if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES]

    def to_action(self) -> Action:
        return Action(
            name=self.name.text().strip(),
            template_path=self.template.currentText(),
            threshold=self.threshold.value(),
            click_offset_x=self.offset_x.value(),
            click_offset_y=self.offset_y.value(),
            poll_interval_s=self.interval.value(),
        )
