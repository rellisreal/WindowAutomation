# WindowAutomation


## Summary:

This is a vibe-coded application for Arch Linux with KDE Plasma as your Desktop Environment. 

### Why?:

This was built to dynamically automate the manual process of installing Neuxs mods through either the Vortex/Amethyst Mod Manger

It can also technically be used for any form of tasks that require manual input when a specific prompt is displayed on screen.

The application built in Python is able to recognise UI elements from template screenshots (Via a library), from there it emuulates a mouse click on them.

### How it works
1. Crop reference images ("templates") of UI elements you want to detect.
2. `windowautomation match <template.png>` captures the screen (via `spectacle`) and locates
   the template with OpenCV template matching.
3. `windowautomation click <template.png>` does the same, then clicks the match's center via
   `ydotool`.
4. Named actions can be stored in a config file and triggered by name (`windowautomation trigger
   <name>`) — useful for binding to a KDE custom keyboard shortcut, since Wayland does not allow
   apps to listen for global hotkeys directly.

### Setup (Arch Linux)

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

### Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Usage

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

### Known limitations
- Display scaling (fractional HiDPI) may cause a mismatch between screenshot pixel coordinates
  and `ydotool`'s input coordinate space — verify with `match` before relying on `click`.
- Continuous polling has a practical floor of ~200-500ms per tick due to `spectacle` process
  spawn overhead.
- For multiple monitors, you're mouse needs to be on the same screen that is being polled (Arch).


### To Do List (Not in any particular order):
- Windows compatibility
- Optimise polling so it's not as intensive with multiple templates/actions being processed. 
- Provide more options rather than just a left mouse click (EG Keyboard Actions, Right Mouse Click, Scroll ETC) 
