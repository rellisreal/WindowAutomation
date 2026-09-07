"""Configuration model and persistence for windowautomation."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "windowautomation" / "config.json"
DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
DEFAULT_YDOTOOL_SOCKET = f"/run/user/{os.getuid()}/.ydotool_socket"


@dataclass
class Action:
    """A single recognize-and-click definition."""

    name: str
    template_path: str
    threshold: float = 0.7
    click_offset_x: int = 0
    click_offset_y: int = 0
    poll_interval_s: float = 1.0
    poll_enabled: bool = False


@dataclass
class Config:
    template_dir: str = str(DEFAULT_TEMPLATE_DIR)
    ydotool_socket: str = DEFAULT_YDOTOOL_SOCKET
    monitor_name: str = ""
    default_threshold: float = 0.7
    guided_capture_delay_s: float = 3.0
    actions: list[Action] = field(default_factory=list)

    def get_action(self, name: str) -> Action | None:
        return next((a for a in self.actions if a.name == name), None)


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    """Load config from disk, returning defaults if the file doesn't exist."""
    if not path.exists():
        return Config()
    data = json.loads(path.read_text())
    actions = [Action(**a) for a in data.get("actions", [])]
    return Config(
        template_dir=data.get("template_dir", str(DEFAULT_TEMPLATE_DIR)),
        ydotool_socket=data.get("ydotool_socket", DEFAULT_YDOTOOL_SOCKET),
        monitor_name=data.get("monitor_name", ""),
        default_threshold=data.get("default_threshold", 0.7),
        guided_capture_delay_s=data.get("guided_capture_delay_s", 3.0),
        actions=actions,
    )


def save_config(config: Config, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "template_dir": config.template_dir,
        "ydotool_socket": config.ydotool_socket,
        "monitor_name": config.monitor_name,
        "default_threshold": config.default_threshold,
        "guided_capture_delay_s": config.guided_capture_delay_s,
        "actions": [asdict(a) for a in config.actions],
    }
    path.write_text(json.dumps(data, indent=2))
