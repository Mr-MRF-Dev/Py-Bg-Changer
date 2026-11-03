"""Reading and writing the config file.

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
from typing import Any

from .errors import ConfigError
from .library import Library
from .state import State

APP_NAME = "py-bg-changer"


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


def _read_raw() -> dict[str, Any]:
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


def _write(data: dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


def load_library() -> Library:
    """The saved wallpapers, aliases and default. Empty if nothing is saved yet."""
    data = _read_raw()
    wallpapers = data.get("wallpapers", {})
    if not isinstance(wallpapers, dict):
        raise ConfigError(
            f"{config_path()}: 'wallpapers' must be an object of name -> path."
        )
    aliases = data.get("aliases", {})
    if not isinstance(aliases, dict):
        raise ConfigError(
            f"{config_path()}: 'aliases' must be an object of alias -> name."
        )
    default = data.get("default")
    return Library(
        wallpapers={str(name): str(path) for name, path in wallpapers.items()},
        aliases={str(alias): str(name) for alias, name in aliases.items()},
        default=default if isinstance(default, str) and default else None,
    )


def save_library(library: Library) -> None:
    """Write the library back in one go, keeping any other keys already in the file."""
    data = _read_raw()
    data["wallpapers"] = library.wallpapers
    for key, value in (("aliases", library.aliases), ("default", library.default)):
        if value:
            data[key] = value
        else:
            data.pop(key, None)
    _write(data)


def load_state() -> State:
    """The image set last and the ones before it. Empty if none is known."""
    data = _read_raw()
    current = data.get("current")
    history = data.get("history")
    items = (
        [item for item in history if isinstance(item, str)]
        if isinstance(history, list)
        else []
    )
    # An earlier format also kept the image that is set now at the end. It does not
    # belong in the history, so drop it.
    while items and items[-1] == current:
        items.pop()
    return State(
        current=current if isinstance(current, str) and current else None,
        history=items,
    )


def save_state(state: State) -> None:
    """Write the state back, keeping any other keys already in the file."""
    data = _read_raw()
    if state.current:
        data["current"] = state.current
    else:
        data.pop("current", None)
    data["history"] = state.history
    _write(data)
