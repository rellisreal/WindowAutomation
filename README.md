# WindowAutomation

Recognize UI elements from template screenshots and click them, on KDE Plasma (Wayland).

## How it works
1. Crop reference images ("templates") of UI elements you want to detect.
2. `windowautomation match <template.png>` captures the screen (via `spectacle`) and locates
   the template with OpenCV template matching.
3. `windowautomation click <template.png>` does the same, then clicks the match's center via
   `ydotool`.
4. Named actions can be stored in a config file and triggered by name (`windowautomation trigger
   <name>`) — useful for binding to a KDE custom keyboard shortcut, since Wayland does not allow
   apps to listen for global hotkeys directly.

## Setup (Arch Linux)

```bash
# Screenshot tool (ships with KDE Plasma; install explicitly if missing)
sudo pacman -S spectacle

# Click simulation tool + its background daemon
sudo pacman -S ydotool

# ydotool needs to talk to /dev/uinput — add yourself to the input group
sudo usermod -aG input "$USER"
# log out/in (or reboot) for the group change to take effect

# Run the daemon (either once per session, or enable as a systemd user service)
ydotoold &
```

The daemon prints its socket path when it starts. The application defaults to the standard
per-user path (`/run/user/<uid>/.ydotool_socket`); use the Settings dialog if your daemon uses
another path.

## Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
# Locate a template on screen and print its coordinates
windowautomation match templates/example.png

# Locate and click its center
windowautomation click templates/example.png

# Run a named action from ~/.config/windowautomation/config.json
windowautomation trigger my-action

# Launch the desktop application
windowautomation-gui
```

## Known limitations
- Display scaling (fractional HiDPI) may cause a mismatch between screenshot pixel coordinates
  and `ydotool`'s input coordinate space — verify with `match` before relying on `click`.
- Continuous polling has a practical floor of ~200-500ms per tick due to `spectacle` process
  spawn overhead.
- Only the single best match is located per template; matching multiple identical on-screen
  instances is not yet supported.
