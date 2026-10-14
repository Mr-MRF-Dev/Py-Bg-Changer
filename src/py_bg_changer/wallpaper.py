"""Set the desktop wallpaper on Windows, macOS and Linux."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path


class WallpaperError(Exception):
    """The wallpaper could not be applied."""


def set_wallpaper(path: Path) -> None:
    path = Path(path).expanduser().resolve()
    system = platform.system()
    if system == "Windows":
        _windows(path)
    elif system == "Darwin":
        _macos(path)
    elif system == "Linux":
        _linux(path)
    else:
        raise WallpaperError(f"Unsupported operating system: {system}")


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    if shutil.which(cmd[0]) is None:
        raise WallpaperError(f"'{cmd[0]}' was not found on this system.")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        raise WallpaperError(f"{cmd[0]} failed: {detail}")
    return result


# --- Windows ---------------------------------------------------------------


def _windows(path: Path) -> None:
    import ctypes

    SPI_SETDESKWALLPAPER = 0x0014
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02
    ok = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER, 0, str(path), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
    )
    if not ok:
        raise WallpaperError("Windows refused to change the wallpaper.")


# --- macOS -----------------------------------------------------------------


def _macos(path: Path) -> None:
    escaped = str(path).replace("\\", "\\\\").replace('"', '\\"')
    script = (
        'tell application "System Events" to tell every desktop '
        f'to set picture to "{escaped}"'
    )
    _run(["osascript", "-e", script])


# --- Linux -----------------------------------------------------------------


def _linux(path: Path) -> None:
    desktop = ":".join(
        filter(
            None,
            [os.environ.get("XDG_CURRENT_DESKTOP"), os.environ.get("DESKTOP_SESSION")],
        )
    ).lower()
    uri = path.as_uri()

    if "cinnamon" in desktop:
        _run(
            ["gsettings", "set", "org.cinnamon.desktop.background", "picture-uri", uri]
        )
    elif "mate" in desktop:
        _run(["gsettings", "set", "org.mate.background", "picture-filename", str(path)])
    elif any(name in desktop for name in ("gnome", "budgie", "unity", "pantheon")):
        _run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri])
        # Newer GNOME has a separate key for dark mode; older versions don't.
        _run(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri-dark",
                uri,
            ],
            check=False,
        )
    elif "kde" in desktop or "plasma" in desktop:
        _run(["plasma-apply-wallpaperimage", str(path)])
    elif "xfce" in desktop:
        _xfce(path)
    elif "sway" in desktop:
        _run(["swaymsg", "output", "*", "bg", str(path), "fill"])
    else:
        _linux_fallback(path)


def _xfce(path: Path) -> None:
    props = _run(["xfconf-query", "-c", "xfce4-desktop", "-l"]).stdout.splitlines()
    targets = [p for p in props if p.endswith("/last-image")]
    if not targets:
        raise WallpaperError("Could not find the XFCE wallpaper settings.")
    for prop in targets:
        _run(["xfconf-query", "-c", "xfce4-desktop", "-p", prop, "-s", str(path)])


def _linux_fallback(path: Path) -> None:
    for cmd in (
        ["feh", "--bg-fill", str(path)],
        ["nitrogen", "--set-zoom-fill", "--save", str(path)],
    ):
        if shutil.which(cmd[0]):
            _run(cmd)
            return
    raise WallpaperError(
        "Could not detect your desktop environment. "
        "Install 'feh' (or 'nitrogen') and try again."
    )
