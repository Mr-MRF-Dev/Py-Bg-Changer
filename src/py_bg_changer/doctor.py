"""`pbc doctor`: show what this program sees, to find out why a wallpaper won't change."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

from . import __version__, cache, config
from .wallpaper import backend_info


def _line(label: str, value: object) -> None:
    print(f"{label:<9} {value}")


def run() -> int:
    problems = 0
    _line("Version:", __version__)
    _line("Python:", f"{platform.python_version()} on {platform.platform()}")
    if platform.system() == "Linux":
        seen = ", ".join(
            f"{name}={os.environ.get(name, '')!r}"
            for name in ("XDG_CURRENT_DESKTOP", "DESKTOP_SESSION", "XDG_SESSION_TYPE")
        )
        _line("Desktop:", seen)

    path = config.config_path()
    _line("Config:", f"{path}" + ("" if path.exists() else "  (not created yet)"))
    _line("Images:", cache.cache_dir())
    try:
        wallpapers = config.load()
        aliases = config.load_aliases()
        default = config.get_default()
    except config.ConfigError as exc:
        problems += 1
        _line("Saved:", f"cannot be read: {exc}")
    else:
        saved = f"{len(wallpapers)} wallpaper(s), {len(aliases)} alias(es)"
        if default:
            saved += f", default: {default}"
        _line("Saved:", saved)
        missing = [
            name
            for name, image in wallpapers.items()
            if not Path(image).expanduser().is_file()
        ]
        if missing:
            problems += 1
            _line("Missing:", f"the image file is gone for: {', '.join(missing)}")

    backend = backend_info()
    _line("Backend:", backend.name)
    if not backend.supported:
        problems += 1
        print(f"  Problem: {backend.note}")
    for tool in backend.tools:
        found = shutil.which(tool)
        print(
            f"  [{'ok' if found else 'missing'}] {tool}"
            + (f"  {found}" if found else "")
        )
    if backend.tools:
        present = [shutil.which(tool) for tool in backend.tools]
        if not (any(present) if backend.any_of else all(present)):
            problems += 1
    for tool in backend.optional:
        found = shutil.which(tool)
        print(
            f"  [{'ok' if found else 'missing'}] {tool} (optional)"
            + (f"  {found}" if found else "")
        )
    if backend.note and backend.supported:
        print(f"  Note: {backend.note}")

    print()
    if problems:
        print(f"Found {problems} problem(s).")
        return 1
    print("Everything looks fine.")
    return 0
