"""Which layout the saved files have.

Version 1 (py-bg-changer 1.x): everything is in `config.json`, even the image that
was set last (`current`) and the ones before it (`history`). Those two change every
time a wallpaper is set, so the file kept being rewritten.

Version 2: `config.json` only holds what the user saved (wallpapers, aliases and the
default). `current` and `history` live in `state.json`, in the folder for things that
change by themselves.

Both files say which version they are in a `"version"` key. Files from 1.x have no such
key: `config.json` of that time is told apart by still holding `current` or `history`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import ConfigError

CURRENT_VERSION = 2

# the keys that moved from config.json to state.json in version 2
STATE_KEYS = ("current", "history")


def declared_version(data: dict[str, Any], path: Path) -> int | None:
    """The version a file says it has, or None if it does not say."""
    version = data.get("version")
    if version is None:
        return None
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ConfigError(f"{path}: 'version' must be a whole number, not {version!r}.")
    return version


def config_version(data: dict[str, Any], path: Path) -> int:
    """The layout of a config.json that was already read."""
    declared = declared_version(data, path)
    if declared is not None:
        return declared
    return 1 if any(key in data for key in STATE_KEYS) else CURRENT_VERSION


def check_supported(version: int, path: Path) -> None:
    """Refuse to read (and so to damage) a file from a newer py-bg-changer."""
    if version > CURRENT_VERSION:
        raise ConfigError(
            f"{path} was written by a newer py-bg-changer "
            f"(file format {version}; this one understands up to {CURRENT_VERSION}).\n"
            "Update py-bg-changer to use it."
        )
