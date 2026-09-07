from pathlib import Path

from windowautomation.config import Action, Config, load_config, save_config
from windowautomation.ui.template_preview import import_templates


def test_config_round_trip(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config = Config(
        template_dir=str(tmp_path / "templates"),
        monitor_name="DP-1",
        actions=[Action(name="foo", template_path="foo.png", threshold=0.9)],
    )

    save_config(config, config_path)
    loaded = load_config(config_path)

    assert loaded.template_dir == config.template_dir
    assert loaded.monitor_name == "DP-1"
    assert len(loaded.actions) == 1
    assert loaded.actions[0].name == "foo"
    assert loaded.actions[0].threshold == 0.9


def test_load_config_missing_file_returns_defaults(tmp_path: Path):
    config = load_config(tmp_path / "does_not_exist.json")

    assert config.actions == []
    assert config.default_threshold == 0.7


def test_get_action_lookup():
    config = Config(actions=[Action(name="a", template_path="a.png")])

    assert config.get_action("a") is not None
    assert config.get_action("missing") is None


def test_import_templates_copies_images(tmp_path: Path):
    source = tmp_path / "source.png"
    source.write_bytes(b"image data")
    target_dir = tmp_path / "templates"

    imported = import_templates([str(source)], str(target_dir))

    assert imported == [str(target_dir / "source.png")]
    assert (target_dir / "source.png").read_bytes() == b"image data"
