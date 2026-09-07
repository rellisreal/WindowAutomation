import numpy as np

from windowautomation.matcher import find_template


def _make_screen_with_patch(patch: np.ndarray, x: int, y: int, size=(200, 200)) -> np.ndarray:
    screen = np.random.randint(0, 255, (size[0], size[1], 3), dtype=np.uint8)
    h, w = patch.shape[:2]
    screen[y : y + h, x : x + w] = patch
    return screen


def test_find_template_locates_known_patch():
    rng = np.random.default_rng(42)
    patch = rng.integers(0, 255, (20, 30, 3), dtype=np.uint8)
    screen = _make_screen_with_patch(patch, x=50, y=70)

    result = find_template(screen, patch, threshold=0.9)

    assert result is not None
    assert (result.x, result.y) == (50, 70)
    assert (result.width, result.height) == (30, 20)
    assert result.confidence > 0.99


def test_find_template_returns_none_when_absent():
    rng = np.random.default_rng(1)
    screen = rng.integers(0, 255, (100, 100, 3), dtype=np.uint8)
    template = rng.integers(0, 255, (20, 20, 3), dtype=np.uint8)

    result = find_template(screen, template, threshold=0.95)

    assert result is None


def test_find_template_returns_none_when_template_larger_than_screen():
    screen = np.zeros((10, 10, 3), dtype=np.uint8)
    template = np.zeros((20, 20, 3), dtype=np.uint8)

    assert find_template(screen, template) is None
