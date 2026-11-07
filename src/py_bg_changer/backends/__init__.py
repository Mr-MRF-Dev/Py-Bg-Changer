"""Setting the desktop wallpaper.

There is one small class per way of doing it (`windows.py`, `gsettings.py`, `kde.py`,
...). `BACKENDS` lists them, and the first one that fits the machine is used. To
support a new desktop, write a class like the ones here and add it to the list.
"""

from __future__ import annotations

from pathlib import Path

from ..errors import WallpaperError
from .base import Backend, BackendInfo, Environment
from .gsettings import Cinnamon, Gnome, Mate
from .kde import Kde
from .macos import MacOS
from .sway import Sway
from .windows import Windows
from .x11 import X11Fallback
from .xfce import Xfce

# The first one that fits wins, so the catch-all has to be the last one.
BACKENDS: list[type[Backend]] = [
    Windows,
    MacOS,
    Cinnamon,
    Mate,
    Gnome,
    Kde,
    Xfce,
    Sway,
    X11Fallback,
]

ISSUES_URL = "https://github.com/Mr-MRF-Dev/Py-Bg-Changer/issues"
WAYLAND_NOTE = (
    "this Wayland desktop is not supported yet (feh and nitrogen only work on X11)"
)


def pick(env: Environment | None = None) -> Backend | None:
    """The backend that fits this machine, or None if there is none."""
    env = env or Environment.detect()
    for backend in BACKENDS:
        if backend.matches(env):
            return backend(env)
    return None


def set_wallpaper(path: Path) -> None:
    path = Path(path).expanduser().resolve()
    env = Environment.detect()
    backend = pick(env)
    if backend is None:
        if env.system == "Linux":
            raise WallpaperError(
                f"Could not detect your desktop environment ({env.describe()}).\n"
                f"This Wayland desktop is not supported yet (feh and nitrogen only work on X11).\n"
                f"Please open an issue with the values above: {ISSUES_URL}"
            )
        raise WallpaperError(f"Unsupported operating system: {env.system}")
    backend.set(path)


def backend_info(env: Environment | None = None) -> BackendInfo:
    """What `set_wallpaper` would use on this machine (shown by `pbc doctor`)."""
    env = env or Environment.detect()
    for backend in BACKENDS:
        if backend.matches(env):
            return backend.info()
    if env.system == "Linux":
        return BackendInfo("none", supported=False, note=WAYLAND_NOTE)
    return BackendInfo(
        "none", supported=False, note=f"unsupported operating system: {env.system}"
    )


__all__ = [
    "BACKENDS",
    "Backend",
    "BackendInfo",
    "Environment",
    "backend_info",
    "pick",
    "set_wallpaper",
]
