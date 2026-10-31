"""Small helpers shared by the tests."""

from pathlib import Path

from py_bg_changer import cli, config


def stored(name):
    """Path of the copy that is kept for a saved name."""
    return Path(config.load()[name])


def add_images(tmp_path, *names):
    """Save one small image per name, each with different content."""
    for name in names:
        f = tmp_path / f"{name}.png"
        f.write_bytes(name.encode())
        cli.main(["add", name, str(f)])
