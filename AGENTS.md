# WindowAutomation

Screenshot-template recognition and click automation for **KDE Plasma on Wayland**. Python + PySide6 GUI, OpenCV template matching, `spectacle` for screenshots, `ydotool` for input simulation.

See [README.md](README.md) for user-facing setup/usage. This file is for AI coding agents.

## Architecture

- `src/windowautomation/capture.py` — screenshot capture via `spectacle` CLI subprocess (no portal dialogs). `capture_monitor()` crops a single monitor's region out of a full-desktop screenshot using scaled geometry.
- `src/windowautomation/matcher.py` — OpenCV template matching.
- `src/windowautomation/input_ctl.py` — `ydotool` wrapper for move/click (talks to `ydotoold` over a unix socket).
- `src/windowautomation/config.py` — `Action`/`Config` dataclasses, JSON persistence at `~/.config/windowautomation/config.json`. `Config.guided_capture_delay_s` controls the guided-capture delay (editable via Settings).
- `src/windowautomation/cli.py` — `match` / `click` / `trigger` subcommands (console script `windowautomation`).
- `src/windowautomation/main.py` + `ui/` — PySide6 desktop app (console script `windowautomation-gui`). `ui/guided_capture.py` drives the delay → capture → click-point/region selection → save-action flow; `ui/main_window.py` is the main window (monitor selector, action/template lists).

## Multi-monitor coordinate handling (Wayland/KDE) — key pitfalls

- **Identify monitors by connector name** (`DP-1`, `HDMI-A-1`), never by list order or index — Qt's `QApplication.screens()` order does not match physical/KScreen order and can vary between runs.
- A full-desktop screenshot from `spectacle` spans the virtual desktop (union of all screen geometries). `capture_monitor()` crops it using each screen's own `geometry()` rect against the virtual rect — this is correct even when monitors differ in resolution/DPI; don't assume screenshot pixels equal a single monitor's logical size.
- `spectacle` writing warnings to stderr (e.g. missing icon themes) is **not** a failure — only treat it as an error if the exit code is non-zero or the output file is missing.
- **Do not try to read the live global cursor position on Wayland, and do not position windows at arbitrary global coordinates.** Both were tried (a transparent overlay spanning all monitors, `QCursor.pos()` + `QApplication.screenAt()`) and failed: plain `xdg_toplevel` windows cannot be positioned by the client on Wayland (only the compositor decides placement), so an overlay "spanning the virtual desktop" actually only lands wherever KWin puts it — silently breaking cursor tracking on whichever monitor the window doesn't happen to cover. Guided capture now avoids this entirely: it hides all of its windows and lets the user select the click point manually on the captured image afterward, instead of trying to auto-detect where the mouse was.

## `ydotool mousemove --absolute` is not real absolute positioning — root cause of "clicks always land top-left"

`ydotool`'s `--absolute` flag (see `Client/tool_mousemove.c` upstream) does **not** use `EV_ABS`. It fakes absolute positioning by emitting a relative move of `INT32_MIN` on both axes first (slamming the cursor to the top-left corner of the whole virtual desktop, since compositors clamp relative moves at the display bounds), then emitting a normal *relative* move of the given `-x/-y` amount from that corner. `ydotool mousemove --help` explicitly warns: *"You need to disable mouse speed acceleration for correct absolute movement."* `ydotoold` only disables libinput pointer acceleration for its virtual device via an `xinput` call gated on `$DISPLAY` being set (X11) — **on a pure Wayland session there is no `$DISPLAY`, so that acceleration-disabling step never runs.** With libinput's default (non-flat) pointer acceleration curve active on the virtual device, the second "relative move by N" gets non-linearly compressed, so the cursor barely leaves the corner regardless of how large `x`/`y` is. This was empirically confirmed: `ydotool mousemove --absolute -x 900 -y 700` and `-x 2200 -y 300` both visually landed at the top-left corner.

**IMPORTANT CORRECTION:** `AttrPointerAccelProfile` is NOT a real libinput quirks attribute (verified against `/usr/share/libinput/*.quirks` on this system — the actual supported `Attr*` keys are things like `AttrSizeHint`, `AttrEventCode`, `AttrIsVirtual`, etc.; there is no static udev/quirks-level override for the pointer acceleration profile). A quirks file using that key is silently a no-op — do not waste time on it.

Pointer acceleration profile is a **runtime libinput API setting** (`libinput_device_config_accel_set_profile`), which KWin exposes per-device in KDE Plasma's **System Settings → Input Devices → Mouse**. The fix is to find the ydotoold virtual device in that per-device list there and set its acceleration profile to "Flat"/none (persisted by KWin, not by a system config file this app can edit). Verify with the manual test above (`ydotool mousemove --absolute -x 900 -y 700`, observe where the cursor actually lands) before assuming any further click-accuracy bug is in this app's Python code.

## Build / test / run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m compileall -q src tests   # quick syntax check
pytest -q                            # test suite (tests/test_*.py)
windowautomation-gui                 # launch the desktop app
```

GUI smoke-testing without a real display: prefix commands with `QT_QPA_PLATFORM=offscreen`. To test against the real Wayland session, use `QT_QPA_PLATFORM=wayland` instead (needed for real monitor geometry/cursor behavior — offscreen fabricates screens).

`ydotoold` must be running (`ydotoold &`) and the user must be in the `input` group for click simulation to work; see [README.md](README.md#setup-arch-linux) for full setup.
