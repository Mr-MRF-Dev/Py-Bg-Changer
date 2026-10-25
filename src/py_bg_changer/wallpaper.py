"""Set the desktop wallpaper on Windows, macOS and Linux."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import NamedTuple


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


def linux_desktop() -> str:
    """The desktop environment as one lowercase string, e.g. "ubuntu:gnome"."""
    return ":".join(
        filter(
            None,
            [os.environ.get("XDG_CURRENT_DESKTOP"), os.environ.get("DESKTOP_SESSION")],
        )
    ).lower()


def _linux_backend(desktop: str) -> str:
    if "cinnamon" in desktop:
        return "cinnamon"
    if "mate" in desktop:
        return "mate"
    if any(name in desktop for name in ("gnome", "budgie", "unity", "pantheon")):
        return "gnome"
    if "kde" in desktop or "plasma" in desktop:
        return "kde"
    if "xfce" in desktop:
        return "xfce"
    if "sway" in desktop:
        return "sway"
    return "fallback"


def _linux(path: Path) -> None:
    backend = _linux_backend(linux_desktop())
    uri = path.as_uri()

    if backend == "cinnamon":
        _run(
            ["gsettings", "set", "org.cinnamon.desktop.background", "picture-uri", uri]
        )
    elif backend == "mate":
        _run(["gsettings", "set", "org.mate.background", "picture-filename", str(path)])
    elif backend == "gnome":
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
    elif backend == "kde":
        _run(["plasma-apply-wallpaperimage", str(path)])
    elif backend == "xfce":
        _xfce(path)
    elif backend == "sway":
        _run(["swaymsg", "output", "*", "bg", str(path), "fill"])
    else:
        _linux_fallback(path)


class Backend(NamedTuple):
    """What `set_wallpaper` would use on this machine (shown by `pbc doctor`)."""

    name: str
    tools: tuple[str, ...] = ()  # commands it needs
    any_of: bool = False  # True when one of the tools is enough
    optional: tuple[str, ...] = ()  # commands that are only sometimes needed
    note: str = ""
    supported: bool = True


_LINUX_TOOLS = {
    "cinnamon": ("gsettings",),
    "mate": ("gsettings",),
    "gnome": ("gsettings",),
    "kde": ("plasma-apply-wallpaperimage",),
    "xfce": ("xfconf-query",),
    "sway": ("swaymsg",),
}


def backend_info() -> Backend:
    system = platform.system()
    if system == "Windows":
        return Backend("windows (SystemParametersInfoW)")
    if system == "Darwin":
        return Backend("macos (osascript)", ("osascript",))
    if system != "Linux":
        return Backend(
            "none", supported=False, note=f"unsupported operating system: {system}"
        )

    backend = _linux_backend(linux_desktop())
    if backend == "fallback":
        if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
            return Backend(
                "none",
                supported=False,
                note="this Wayland desktop is not supported yet "
                "(feh and nitrogen only work on X11)",
            )
        return Backend("fallback (feh or nitrogen)", ("feh", "nitrogen"), any_of=True)
    if backend == "xfce":
        return Backend(
            "xfce",
            _LINUX_TOOLS[backend],
            optional=("xrandr",),
            note="xrandr is only needed on a fresh XFCE with no wallpaper settings yet",
        )
    return Backend(backend, _LINUX_TOOLS[backend])


def _xfce(path: Path) -> None:
    props = _run(["xfconf-query", "-c", "xfce4-desktop", "-l"]).stdout.splitlines()
    targets = [p for p in props if p.endswith("/last-image")]
    for prop in targets:
        _run(["xfconf-query", "-c", "xfce4-desktop", "-p", prop, "-s", str(path)])
    if targets:
        return

    # A fresh XFCE has no wallpaper settings until one is picked in Settings >
    # Desktop, so create them: one per monitor and workspace, which is how
    # xfdesktop names them (the monitor is its RandR/connector name, e.g. eDP-1).
    monitors = _xfce_monitors()
    workspaces = _xfce_workspace_count()
    for monitor in monitors:
        for number in range(workspaces):
            prop = f"/backdrop/screen0/monitor{monitor}/workspace{number}/last-image"
            _run(
                ["xfconf-query", "-c", "xfce4-desktop", "-p", prop]
                + ["--create", "-t", "string", "-s", str(path)]
            )


def _xfce_monitors() -> list[str]:
    hint = (
        "Could not find the XFCE wallpaper settings. Pick a wallpaper once in "
        "Settings > Desktop to create them, or install 'xrandr' so "
        "they can be created automatically."
    )
    if shutil.which("xrandr") is None:
        raise WallpaperError(hint)
    lines = _run(["xrandr", "--listmonitors"]).stdout.splitlines()[1:]
    # " 0: +*eDP-1 1920/344x1080/194+0+0  eDP-1": the name is the last word
    monitors = [line.split()[-1] for line in lines if line.strip()]
    if not monitors:
        raise WallpaperError(hint)
    return monitors


def _xfce_workspace_count() -> int:
    result = _run(
        ["xfconf-query", "-c", "xfwm4", "-p", "/general/workspace_count"], check=False
    )
    try:
        return min(max(int(result.stdout.strip()), 1), 64)
    except ValueError:
        return 4  # xfwm4's default when the setting does not exist


def _linux_fallback(path: Path) -> None:
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()

    # feh and nitrogen only draw on X11. On Wayland they would run without error
    # and change nothing, so they are not even tried there.
    if session != "wayland":
        for cmd in (
            ["feh", "--bg-fill", str(path)],
            ["nitrogen", "--set-zoom-fill", "--save", str(path)],
        ):
            if shutil.which(cmd[0]):
                _run(cmd)
                return

    seen = ", ".join(
        f"{name}={os.environ.get(name, '')!r}"
        for name in ("XDG_CURRENT_DESKTOP", "DESKTOP_SESSION", "XDG_SESSION_TYPE")
    )
    if session == "wayland":
        hint = (
            "This Wayland desktop is not supported yet (feh and nitrogen only work on X11).\n"
            "Please open an issue with the values above: "
            "https://github.com/Mr-MRF-Dev/Py-Bg-Changer/issues"
        )
    else:
        hint = "Install 'feh' (or 'nitrogen') and try again."
    raise WallpaperError(f"Could not detect your desktop environment ({seen}).\n{hint}")
