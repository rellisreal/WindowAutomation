"""Mouse control via `ydotool` (requires `ydotoold` running and user in `input` group)."""

from __future__ import annotations

import os
import shutil
import subprocess

LEFT_CLICK = "0xC0"


class InputError(RuntimeError):
    """Raised when a ydotool command could not be executed."""


def _check_ydotool_available() -> None:
    if shutil.which("ydotool") is None:
        raise InputError(
            "'ydotool' was not found on PATH. Install it with: sudo pacman -S ydotool"
        )


def _run(args: list[str], socket_path: str) -> None:
    _check_ydotool_available()
    env = os.environ.copy()
    env["YDOTOOL_SOCKET"] = socket_path
    result = subprocess.run(["ydotool", *args], capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise InputError(
            f"ydotool {' '.join(args)} failed: {result.stderr.strip()}. "
            "Is ydotoold running and is your user in the 'input' group?"
        )


def move_to(x: int, y: int, socket_path: str = "/tmp/.ydotool_socket") -> None:
    # ydotool's own --absolute flag does a reset-jump + relative-move internally and is
    # unreliable in practice; do the same trick ourselves as two separate commands so
    # each move is fully flushed before the next is issued.
    _run(["mousemove", "-x", "-100000", "-y", "-100000"], socket_path)
    _run(["mousemove", "-x", str(x), "-y", str(y)], socket_path)


def click(x: int, y: int, socket_path: str = "/tmp/.ydotool_socket") -> None:
    """Move to (x, y) then perform a left click."""
    move_to(x, y, socket_path)
    _run(["click", LEFT_CLICK], socket_path)
