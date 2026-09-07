from __future__ import annotations

from pathlib import Path

import cv2
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from windowautomation import capture, input_ctl
from windowautomation.config import Action, Config, save_config
from windowautomation.matcher import find_template
from windowautomation.ui.action_dialog import ActionDialog
from windowautomation.ui.guided_capture import GuidedCaptureDialog
from windowautomation.ui.settings_dialog import SettingsDialog
from windowautomation.ui.template_preview import TemplatePreview, import_templates


class MainWindow(QMainWindow):
    def __init__(self, config: Config, config_path: Path | None = None):
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.run_tick)
        self.setWindowTitle("WindowAutomation")
        self.resize(1100, 700)

        self.action_list = QListWidget()
        self.action_list.currentRowChanged.connect(self._update_poll_interval)
        self.template_list = QListWidget()
        self.template_list.currentRowChanged.connect(self._template_selected)
        self.preview_enabled = QCheckBox("Show template preview")
        self.preview_enabled.setChecked(True)
        self.preview_enabled.toggled.connect(self._refresh_preview)
        self.preview = TemplatePreview()
        self.preview.pointSelected.connect(self._set_click_point)
        self.status = QLabel("Ready")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.interval = QSpinBox()
        self.interval.setRange(100, 60000)
        self.interval.setSuffix(" ms")
        self.interval.setValue(1000)
        self.offset_x = QSpinBox()
        self.offset_x.setRange(-10000, 10000)
        self.offset_x.setPrefix("X ")
        self.offset_y = QSpinBox()
        self.offset_y.setRange(-10000, 10000)
        self.offset_y.setPrefix("Y ")
        self.offset_x.valueChanged.connect(self._update_click_offset)
        self.offset_y.valueChanged.connect(self._update_click_offset)
        self.run_button = QPushButton("Run once")
        self.poll_button = QPushButton("Start polling")
        self.settings_button = QPushButton("Settings")
        self.run_all_checkbox = QCheckBox("Cycle through all actions")
        self.monitor = QComboBox()
        self._populate_monitors()
        self.run_button.clicked.connect(self.run_tick)
        self.poll_button.clicked.connect(self.toggle_polling)
        self.settings_button.clicked.connect(self.open_settings)
        self.add_button = QPushButton("Add Template")
        self.add_button.clicked.connect(self.add_template)
        self.create_action_button = QPushButton("Create action")
        self.create_action_button.clicked.connect(self.create_action)
        self.edit_action_button = QPushButton("Edit action")
        self.edit_action_button.clicked.connect(self.edit_action)
        self.guided_button = QPushButton("Guided capture")
        self.guided_button.clicked.connect(self.guided_capture)
        self.delete_template_button = QPushButton("Delete template")
        self.delete_template_button.clicked.connect(self.delete_template)
        self.delete_action_button = QPushButton("Delete action")
        self.delete_action_button.clicked.connect(self.delete_action)

        controls = QHBoxLayout()
        controls.addWidget(self.run_button)
        controls.addWidget(self.poll_button)
        controls.addWidget(self.run_all_checkbox)
        controls.addWidget(QLabel("Interval"))
        controls.addWidget(self.interval)
        controls.addWidget(QLabel("Click offset"))
        controls.addWidget(self.offset_x)
        controls.addWidget(self.offset_y)
        controls.addStretch()
        controls.addWidget(self.settings_button)

        content = QWidget()
        layout = QVBoxLayout(content)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_panel = QWidget()
        left_panel.setMinimumWidth(260)
        left = QVBoxLayout(left_panel)
        right_panel = QWidget()
        right = QVBoxLayout(right_panel)
        left.addWidget(QLabel("Actions"))
        left.addWidget(self.action_list)
        left.addWidget(QLabel("Capture monitor"))
        left.addWidget(self.monitor)
        left.addWidget(QLabel("Templates"))
        left.addWidget(self.template_list)
        left.addWidget(self.add_button)
        left.addWidget(self.create_action_button)
        left.addWidget(self.edit_action_button)
        left.addWidget(self.guided_button)
        left.addWidget(self.delete_template_button)
        left.addWidget(self.delete_action_button)
        left.addStretch()
        right.addWidget(self.preview_enabled)
        right.addWidget(self.preview, 1)
        right.addLayout(controls)
        right.addWidget(self.status)
        right.addWidget(self.log, 1)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)
        self.setStyleSheet("""
            QMainWindow { background: #f4f6f8; }
            QLabel { color: #344054; }
            QListWidget, QPlainTextEdit, QComboBox, QSpinBox { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 5px; padding: 4px; color: #1f2937; }
            QComboBox QAbstractItemView { background: #ffffff; color: #1f2937; selection-background-color: #dbeafe; selection-color: #1e3a8a; }
            QListWidget::item:selected { background: #dbeafe; color: #1e3a8a; }
            QPushButton { background: #ffffff; border: 1px solid #94a3b8; border-radius: 5px; padding: 7px 10px; color: #1f2937; }
            QPushButton:hover { background: #e0f2fe; }
            QCheckBox { color: #1f2937; padding: 4px; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #94a3b8; border-radius: 3px; background: #ffffff; }
            QCheckBox::indicator:checked { background: #2563eb; border-color: #2563eb; }
            QCheckBox::indicator:hover { border-color: #2563eb; }
        """)
        self.setCentralWidget(content)
        self.refresh_actions()
        self.refresh_templates()

    def _populate_monitors(self) -> None:
        self.monitor.clear()
        for screen in self.screen_list():
            geometry = screen.geometry()
            label = f"{screen.name()} at ({geometry.x()}, {geometry.y()}) - {geometry.width()}x{geometry.height()}"
            self.monitor.addItem(label, screen.name())
        index = self.monitor.findData(self.config.monitor_name)
        if index >= 0:
            self.monitor.setCurrentIndex(index)

    @staticmethod
    def screen_list():
        from PySide6.QtWidgets import QApplication
        return QApplication.screens()

    def selected_screen(self):
        screens = self.screen_list()
        selected_name = self.monitor.currentData()
        return next((screen for screen in screens if screen.name() == selected_name), None)

    def guided_capture(self) -> None:
        screen = self.selected_screen()
        if screen is None:
            QMessageBox.warning(self, "Guided capture", "No monitor is available.")
            return
        self.config.monitor_name = screen.name()
        dialog = GuidedCaptureDialog(screen, self.screen_list(), self.config.template_dir, self.config.guided_capture_delay_s, self)
        # show() + setModal(True) instead of exec(): exec()'s nested event loop is torn
        # down as soon as the dialog is hidden, which breaks the hide-during-capture flow.
        dialog.finished.connect(lambda result: self._guided_capture_finished(dialog, result))
        dialog.show()

    def _guided_capture_finished(self, dialog: GuidedCaptureDialog, result: int) -> None:
        if not result:
            return
        x, y = dialog.click_offset
        name = Path(dialog.template_path).stem
        existing = self.config.get_action(name)
        if existing is not None:
            # Redoing a capture with the same name should update it in place, not
            # pile up a duplicate entry that shadows the fresh click offset.
            existing.template_path = dialog.template_path
            existing.click_offset_x = x
            existing.click_offset_y = y
        else:
            self.config.actions.append(Action(name=name, template_path=dialog.template_path, click_offset_x=x, click_offset_y=y))
        if self.config_path:
            save_config(self.config, self.config_path)
        self.refresh_actions()
        self.refresh_templates()
        self._select_action_by_name(name)
        self._report(f"Created guided action: {name}")

    def refresh_actions(self) -> None:
        self.action_list.clear()
        self.action_list.addItems(action.name for action in self.config.actions)
        if self.config.actions:
            self.action_list.setCurrentRow(0)

    def _select_action_by_name(self, name: str) -> None:
        for row in range(self.action_list.count()):
            if self.action_list.item(row).text() == name:
                self.action_list.setCurrentRow(row)
                return

    def refresh_templates(self) -> None:
        self.template_list.clear()
        template_dir = Path(self.config.template_dir).expanduser()
        paths = sorted(path for path in template_dir.iterdir() if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}) if template_dir.exists() else []
        self.template_list.addItems(path.name for path in paths)
        if paths:
            self.template_list.setCurrentRow(0)

    def _template_selected(self, row: int) -> None:
        if row < 0:
            return
        path = Path(self.config.template_dir).expanduser() / self.template_list.item(row).text()
        self.preview.set_preview(str(path), self.preview_enabled.isChecked())

    def _refresh_preview(self, visible: bool) -> None:
        row = self.template_list.currentRow()
        if row >= 0:
            self._template_selected(row)

    def _set_click_point(self, x: int, y: int) -> None:
        action = self.selected_action()
        template = self._selected_template_path()
        if action is None or template is None:
            return
        image = cv2.imread(template)
        if image is None:
            return
        action.template_path = template
        action.click_offset_x = x
        action.click_offset_y = y
        self.offset_x.setValue(action.click_offset_x)
        self.offset_y.setValue(action.click_offset_y)
        self._report(f"{action.name}: click point set to ({x}, {y})")
        if self.config_path:
            save_config(self.config, self.config_path)

    def _selected_template_path(self) -> str | None:
        row = self.template_list.currentRow()
        if row < 0:
            return None
        return str(Path(self.config.template_dir).expanduser() / self.template_list.item(row).text())

    def delete_template(self) -> None:
        path = self._selected_template_path()
        if path is None:
            return
        answer = QMessageBox.question(self, "Delete template", f"Delete '{Path(path).name}' from disk?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            Path(path).unlink()
        except OSError as exc:
            QMessageBox.critical(self, "Delete template", str(exc))
            return
        self.config.actions = [action for action in self.config.actions if Path(action.template_path).resolve() != Path(path).resolve()]
        if self.config_path:
            save_config(self.config, self.config_path)
        self.refresh_actions()
        self.refresh_templates()
        self._report(f"Deleted template: {Path(path).name}")

    def delete_action(self) -> None:
        action = self.selected_action()
        if action is None:
            return
        answer = QMessageBox.question(self, "Delete action", f"Delete action '{action.name}'?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.config.actions.remove(action)
        if self.config_path:
            save_config(self.config, self.config_path)
        self.refresh_actions()
        self._report(f"Deleted action: {action.name}")

    def add_template(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Add templates", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        self._import_dropped_templates(paths)

    def create_action(self) -> None:
        dialog = ActionDialog(self.config, parent=self)
        if not dialog.exec():
            return
        action = dialog.to_action()
        if not action.name or not action.template_path:
            QMessageBox.warning(self, "Create action", "Choose a template and enter an action name.")
            return
        if self.config.get_action(action.name) is not None:
            QMessageBox.warning(self, "Create action", f"An action named '{action.name}' already exists.")
            return
        self.config.actions.append(action)
        if self.config_path:
            save_config(self.config, self.config_path)
        self.refresh_actions()
        self._select_action_by_name(action.name)
        template_name = Path(action.template_path).name
        for row in range(self.template_list.count()):
            if self.template_list.item(row).text() == template_name:
                self.template_list.setCurrentRow(row)
                break
        self._report(f"Created action: {action.name}")

    def edit_action(self) -> None:
        action = self.selected_action()
        if action is None:
            QMessageBox.information(self, "Edit action", "Select an action first.")
            return
        dialog = ActionDialog(self.config, action=action, parent=self)
        if not dialog.exec():
            return
        updated = dialog.to_action()
        if not updated.name or not updated.template_path:
            QMessageBox.warning(self, "Edit action", "Choose a template and enter an action name.")
            return
        existing = self.config.get_action(updated.name)
        if existing is not None and existing is not action:
            QMessageBox.warning(self, "Edit action", f"An action named '{updated.name}' already exists.")
            return
        action.name = updated.name
        action.template_path = updated.template_path
        action.threshold = updated.threshold
        action.click_offset_x = updated.click_offset_x
        action.click_offset_y = updated.click_offset_y
        action.poll_interval_s = updated.poll_interval_s
        if self.config_path:
            save_config(self.config, self.config_path)
        row = self.action_list.currentRow()
        self.refresh_actions()
        self.action_list.setCurrentRow(row)
        self._report(f"Updated action: {action.name}")

    def _import_dropped_templates(self, paths: list[str]) -> None:
        if not paths:
            return
        imported = import_templates(paths, self.config.template_dir)
        for path in imported:
            if self.config.get_action(Path(path).stem) is None:
                self.config.actions.append(Action(name=Path(path).stem, template_path=path))
        if self.config_path:
            save_config(self.config, self.config_path)
        self.refresh_actions()
        self.refresh_templates()
        self._report(f"Imported {len(imported)} template(s)")

    def selected_action(self) -> Action | None:
        row = self.action_list.currentRow()
        return self.config.actions[row] if 0 <= row < len(self.config.actions) else None

    def _update_poll_interval(self, row: int) -> None:
        action = self.config.actions[row] if 0 <= row < len(self.config.actions) else None
        if action is not None:
            self.interval.setValue(max(100, round(action.poll_interval_s * 1000)))
            self.offset_x.blockSignals(True)
            self.offset_y.blockSignals(True)
            self.offset_x.setValue(action.click_offset_x)
            self.offset_y.setValue(action.click_offset_y)
            self.offset_x.blockSignals(False)
            self.offset_y.blockSignals(False)

    def _update_click_offset(self) -> None:
        action = self.selected_action()
        if action is None:
            return
        action.click_offset_x = self.offset_x.value()
        action.click_offset_y = self.offset_y.value()
        if self.config_path:
            save_config(self.config, self.config_path)

    def run_selected(self) -> None:
        action = self.selected_action()
        if action is None:
            self.status.setText("No action selected")
            return
        template = cv2.imread(action.template_path)
        if template is None:
            self._report(f"{action.name}: cannot read {action.template_path}")
            return
        try:
            result = find_template(capture.capture_screen(), template, action.threshold)
            if result is None:
                self._report(f"{action.name}: no match above {action.threshold:.2f}")
                return
            x, y = result.x, result.y
            click_x, click_y = x + action.click_offset_x, y + action.click_offset_y
            input_ctl.click(click_x, click_y, self.config.ydotool_socket)
            self._report(f"{action.name}: matched ({x}, {y}), clicked ({click_x}, {click_y}), confidence {result.confidence:.3f}")
        except (capture.CaptureError, input_ctl.InputError) as exc:
            self._report(f"{action.name}: {exc}")

    def run_tick(self) -> None:
        if self.run_all_checkbox.isChecked():
            self.run_all_actions()
        else:
            self.run_selected()

    def run_all_actions(self) -> None:
        if not self.config.actions:
            self.status.setText("No actions configured")
            return
        try:
            screen = capture.capture_screen()
        except capture.CaptureError as exc:
            self._report(f"Capture failed: {exc}")
            return
        for action in self.config.actions:
            template = cv2.imread(action.template_path)
            if template is None:
                continue
            result = find_template(screen, template, action.threshold)
            if result is None:
                continue
            x, y = result.x, result.y
            click_x, click_y = x + action.click_offset_x, y + action.click_offset_y
            try:
                input_ctl.click(click_x, click_y, self.config.ydotool_socket)
            except input_ctl.InputError as exc:
                self._report(f"{action.name}: {exc}")
                return
            self._report(f"{action.name}: matched ({x}, {y}), clicked ({click_x}, {click_y}), confidence {result.confidence:.3f}")
            return
        self._report(f"No match among {len(self.config.actions)} action(s)")

    def toggle_polling(self) -> None:
        if self.poll_timer.isActive():
            self.poll_timer.stop()
            self.poll_button.setText("Start polling")
            self.status.setText("Polling stopped")
            return
        if not self.run_all_checkbox.isChecked() and self.selected_action() is None:
            QMessageBox.information(self, "Polling", "Select an action first.")
            return
        self.poll_timer.start(self.interval.value())
        self.poll_button.setText("Stop polling")
        self.status.setText("Polling active")
        self.run_tick()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            dialog.apply_to(self.config)
            if self.config_path:
                save_config(self.config, self.config_path)
            self._report("Settings saved")

    def _report(self, message: str) -> None:
        self.status.setText(message)
        self.log.appendPlainText(message)
