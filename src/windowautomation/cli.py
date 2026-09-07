"""Command-line entry point for windowautomation."""

from __future__ import annotations

import argparse
import sys

import cv2

from windowautomation import capture, input_ctl
from windowautomation.config import load_config
from windowautomation.matcher import find_template


def _do_match(template_path: str, threshold: float) -> int:
    template = cv2.imread(template_path)
    if template is None:
        print(f"Could not read template image: {template_path}", file=sys.stderr)
        return 1

    screen = capture.capture_screen()
    result = find_template(screen, template, threshold)
    if result is None:
        print("No match found above threshold.")
        return 1

    cx, cy = result.center
    print(f"Match at ({result.x}, {result.y}) size {result.width}x{result.height} "
          f"center ({cx}, {cy}) confidence {result.confidence:.3f}")
    return 0


def _do_click(template_path: str, threshold: float, socket_path: str, offset_x: int = 0, offset_y: int = 0) -> int:
    template = cv2.imread(template_path)
    if template is None:
        print(f"Could not read template image: {template_path}", file=sys.stderr)
        return 1

    screen = capture.capture_screen()
    result = find_template(screen, template, threshold)
    if result is None:
        print("No match found above threshold; not clicking.")
        return 1

    cx, cy = result.x, result.y
    x, y = cx + offset_x, cy + offset_y
    input_ctl.click(x, y, socket_path)
    print(f"Clicked at ({x}, {y}) confidence {result.confidence:.3f}")
    return 0


def _do_trigger(action_name: str) -> int:
    config = load_config()
    action = config.get_action(action_name)
    if action is None:
        print(f"No action named '{action_name}' in config.", file=sys.stderr)
        return 1
    return _do_click(action.template_path, action.threshold, config.ydotool_socket, action.click_offset_x, action.click_offset_y)


def main() -> int:
    parser = argparse.ArgumentParser(prog="windowautomation")
    sub = parser.add_subparsers(dest="command", required=True)

    match_p = sub.add_parser("match", help="Find a template on screen and print its location")
    match_p.add_argument("template", help="Path to template image")
    match_p.add_argument("--threshold", type=float, default=0.85)

    click_p = sub.add_parser("click", help="Find a template on screen and click its center")
    click_p.add_argument("template", help="Path to template image")
    click_p.add_argument("--threshold", type=float, default=0.85)
    click_p.add_argument("--socket", default="/tmp/.ydotool_socket")

    trigger_p = sub.add_parser("trigger", help="Run a configured action by name")
    trigger_p.add_argument("action", help="Action name from config")

    args = parser.parse_args()

    try:
        if args.command == "match":
            return _do_match(args.template, args.threshold)
        if args.command == "click":
            return _do_click(args.template, args.threshold, args.socket)
        if args.command == "trigger":
            return _do_trigger(args.action)
    except (capture.CaptureError, input_ctl.InputError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
