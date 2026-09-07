"""Screen capture via KDE's `spectacle` CLI (Wayland-native, no portal dialog)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image


class CaptureError(RuntimeError):
    """Raised when a screenshot could not be captured."""


def _check_spectacle_available() -> None:
    if shutil.which("spectacle") is None:
        raise CaptureError(
            "'spectacle' was not found on PATH. Install it with: sudo pacman -S spectacle"
        )


def capture_screen() -> np.ndarray:
    """Capture the full screen and return it as a BGR numpy array (OpenCV convention)."""
    _check_spectacle_available()
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir) / "capture.png"
        result = subprocess.run(
            ["spectacle", "-b", "-n", "-o", str(out_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0 or not out_path.exists():
            raise CaptureError(
                f"spectacle failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        image = Image.open(out_path).convert("RGB")
        return np.array(image)[:, :, ::-1].copy()  # RGB -> BGR


def capture_current_monitor() -> np.ndarray:
    """Capture the monitor containing the pointer."""
    _check_spectacle_available()
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir) / "capture.png"
        command = ["spectacle", "-b", "-n", "-m", "-o", str(out_path)]
        result = None
        for attempt in range(2):
            result = subprocess.run(command, capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and out_path.exists():
                break
            if attempt == 0:
                time.sleep(0.2)
        if result is None or result.returncode != 0 or not out_path.exists():
            details = result.stderr.strip() if result else "no process result"
            raise CaptureError(f"spectacle failed (exit {result.returncode if result else 'unknown'}): {details}")
        image = Image.open(out_path).convert("RGB")
        return np.array(image)[:, :, ::-1].copy()


def capture_monitor(screen_rect: tuple[int, int, int, int], virtual_rect: tuple[int, int, int, int]) -> np.ndarray:
    """Capture the full desktop and crop the requested monitor geometry."""
    image = capture_screen()
    screen_x, screen_y, screen_width, screen_height = screen_rect
    virtual_x, virtual_y, virtual_width, virtual_height = virtual_rect
    scale_x = image.shape[1] / virtual_width
    scale_y = image.shape[0] / virtual_height
    left = round((screen_x - virtual_x) * scale_x)
    top = round((screen_y - virtual_y) * scale_y)
    right = left + round(screen_width * scale_x)
    bottom = top + round(screen_height * scale_y)
    return image[top:bottom, left:right].copy()
