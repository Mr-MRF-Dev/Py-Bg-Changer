"""Reading and writing the two files of the program.

`config.json` holds what the user saved. Its format is the same as the original
bg.py, plus an optional default and optional aliases (extra names for a wallpaper):

    {
      "version": 2,
      "wallpapers": {"night": "/path/to/image.jpg"},
      "aliases": {"n": "night", "dark": "night"},
      "default": "night"
    }

`state.json` holds what the program remembers by itself, so that setting a wallpaper
never rewrites the config:

    {"version": 2, "current": "/path/to/image.jpg", "history": ["/path/to/older.jpg"]}

See `schema.py` for the versions and `migrations.py` for how old files are moved.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Any

from . import jsonfile, schema
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


def state_dir() -> Path:
    """Where things that change by themselves go (not the user's own settings)."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(
            os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
        )
    return base / APP_NAME


def state_path() -> Path:
    """Default location, or whatever PBC_STATE points to.

    With a custom PBC_CONFIG the state is kept next to it, so that pointing the
    program at another config also gives it another state.
    """
    override = os.environ.get("PBC_STATE")
    if override:
        return Path(override).expanduser()
    if os.environ.get("PBC_CONFIG"):
        return config_path().with_name("state.json")
    return state_dir() / "state.json"


def _read_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {}
    data = jsonfile.read(path)
    schema.check_supported(schema.config_version(data, path), path)
    return data


def load_library() -> Library:
    """The saved wallpapers, aliases and default. Empty if nothing is saved yet."""
    data = _read_config()
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
    path = config_path()
    data = _read_config()
    data["wallpapers"] = library.wallpapers
    for key, value in (("aliases", library.aliases), ("default", library.default)):
        if value:
            data[key] = value
        else:
            data.pop(key, None)
    # A file that still holds the state of version 1 has to be migrated first.
    if schema.config_version(data, path) >= schema.CURRENT_VERSION:
        data["version"] = schema.CURRENT_VERSION
    jsonfile.write(path, data)


def _read_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return {}
    data = jsonfile.read(path)
    schema.check_supported(schema.declared_version(data, path) or 1, path)
    return data


def load_state() -> State:
    """The image set last and the ones before it. Empty if none is known."""
    data = _read_state()
    current = data.get("current")
    history = data.get("history")
    return State(
        current=current if isinstance(current, str) and current else None,
        history=(
            [item for item in history if isinstance(item, str)]
            if isinstance(history, list)
            else []
        ),
    )


def save_state(state: State) -> None:
    """Write the state back, keeping any other keys already in the file."""
    data = _read_state()
    data["version"] = schema.CURRENT_VERSION
    if state.current:
        data["current"] = state.current
    else:
        data.pop("current", None)
    data["history"] = state.history
    jsonfile.write(state_path(), data)
