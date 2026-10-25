"""Reading and writing the saved wallpapers and the chosen default.

The file format is the same as the original bg.py, plus an optional default and
optional aliases (extra names for a saved wallpaper):

    {
      "wallpapers": {"night": "/path/to/image.jpg"},
      "aliases": {"n": "night", "dark": "night"},
      "default": "night"
    }
"""

from __future__ import annotations

import json
import os
import platform
from pathlib import Path

APP_NAME = "py-bg-changer"
HISTORY_LIMIT = 5  # how many previous images `pbc back` can walk through


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


def _write(data: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


def load() -> dict[str, str]:
    """Return the saved wallpapers as {name: path}. Empty if nothing is saved yet."""
    wallpapers = _read_raw().get("wallpapers", {})
    if not isinstance(wallpapers, dict):
        raise ConfigError(
            f"{config_path()}: 'wallpapers' must be an object of name -> path."
        )
    return {str(name): str(path) for name, path in wallpapers.items()}


def load_aliases() -> dict[str, str]:
    """Return the aliases as {alias: wallpaper name}. Empty if there are none."""
    aliases = _read_raw().get("aliases", {})
    if not isinstance(aliases, dict):
        raise ConfigError(
            f"{config_path()}: 'aliases' must be an object of alias -> name."
        )
    return {str(alias): str(name) for alias, name in aliases.items()}


def save(wallpapers: dict[str, str], aliases: dict[str, str] | None = None) -> None:
    """Write the wallpapers back, keeping any other keys already in the file.

    The aliases are only touched when they are passed in.
    """
    data = _read_raw()
    data["wallpapers"] = wallpapers
    if aliases is not None:
        if aliases:
            data["aliases"] = aliases
        else:
            data.pop("aliases", None)
    _write(data)


def get_default() -> str | None:
    """Name of the wallpaper that a plain `pbc` sets, if one was chosen."""
    value = _read_raw().get("default")
    return value if isinstance(value, str) and value else None


def _history_of(data: dict) -> list[str]:
    history = data.get("history")
    if not isinstance(history, list):
        return []
    items = [item for item in history if isinstance(item, str)]
    # An earlier format also kept the image that is set now at the end. It does not
    # belong here, so drop it.
    while items and items[-1] == data.get("current"):
        items.pop()
    return items


def get_history() -> list[str]:
    """The previous images, oldest first. It works like a stack: `back` takes the last."""
    return _history_of(_read_raw())


def get_current() -> str | None:
    """Path of the image this program set last, if it is known."""
    value = _read_raw().get("current")
    return value if isinstance(value, str) and value else None


def set_current(path: str) -> None:
    """Remember which image was set last. The one it replaces goes on the history."""
    data = _read_raw()
    history = _history_of(data)
    previous = data.get("current")
    if isinstance(previous, str) and previous and previous != path:
        history.append(previous)
    data["current"] = path
    data["history"] = history[-HISTORY_LIMIT:]
    _write(data)


def step_back(current: str, history: list[str]) -> None:
    """Make `current` the image that is set now, with `history` left behind it."""
    data = _read_raw()
    data["current"] = current
    data["history"] = history
    _write(data)


def set_default(name: str | None) -> None:
    """Choose the default wallpaper, or pass None to clear the choice."""
    data = _read_raw()
    if name is None:
        data.pop("default", None)
    else:
        data["default"] = name
    _write(data)
