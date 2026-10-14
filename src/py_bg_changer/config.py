"""Reading and writing the list of saved wallpapers.

The file format is the same as the original bg.py:

    {"wallpapers": {"name": "/path/to/image.jpg"}}
"""

from __future__ import annotations

import json
import os
import platform
from pathlib import Path

APP_NAME = "py-bg-changer"


class ConfigError(Exception):
    """The config file exists but cannot be used."""


def config_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_NAME


def config_path() -> Path:
    """Default location, or whatever PBC_CONFIG points to."""
    override = os.environ.get("PBC_CONFIG")
    if override:
        return Path(override).expanduser()
    return config_dir() / "config.json"


def _read_raw() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Could not read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path} has an unexpected format (expected a JSON object).")
    return data


def load() -> dict[str, str]:
    """Return the saved wallpapers as {name: path}. Empty if nothing is saved yet."""
    wallpapers = _read_raw().get("wallpapers", {})
    if not isinstance(wallpapers, dict):
        raise ConfigError(f"{config_path()}: 'wallpapers' must be an object of name -> path.")
    return {str(name): str(path) for name, path in wallpapers.items()}


def save(wallpapers: dict[str, str]) -> None:
    """Write the wallpapers back, keeping any other keys already in the file."""
    data = _read_raw()
    data["wallpapers"] = wallpapers
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
