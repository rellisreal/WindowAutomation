"""Template matching using OpenCV's matchTemplate."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class MatchResult:
    x: int
    y: int
    width: int
    height: int
    confidence: float

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2


def find_template(
    screen: np.ndarray, template: np.ndarray, threshold: float = 0.7
) -> MatchResult | None:
    """Return the best match of `template` within `screen`, or None if below threshold."""
    if template.shape[0] > screen.shape[0] or template.shape[1] > screen.shape[1]:
        return None

    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val < threshold:
        return None

    h, w = template.shape[:2]
    return MatchResult(x=max_loc[0], y=max_loc[1], width=w, height=h, confidence=max_val)
