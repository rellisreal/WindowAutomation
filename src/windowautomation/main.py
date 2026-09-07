from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from windowautomation.config import DEFAULT_CONFIG_PATH, load_config
from windowautomation.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow(load_config(), DEFAULT_CONFIG_PATH)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
