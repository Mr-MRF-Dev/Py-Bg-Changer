"""XFCE."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..errors import WallpaperError
from .base import LinuxDesktop


class Xfce(LinuxDesktop):
    name = "xfce"
    tools = ("xfconf-query",)
    optional = ("xrandr",)
    note = "xrandr is only needed on a fresh XFCE with no wallpaper settings yet"
    keywords = ("xfce",)

    def set(self, path: Path) -> None:
        props = self.run(
            ["xfconf-query", "-c", "xfce4-desktop", "-l"]
        ).stdout.splitlines()
        targets = [p for p in props if p.endswith("/last-image")]
        for prop in targets:
            self.run(
                ["xfconf-query", "-c", "xfce4-desktop", "-p", prop, "-s", str(path)]
            )
        if targets:
            return

        # A fresh XFCE has no wallpaper settings until one is picked in Settings >
        # Desktop, so create them: one per monitor and workspace, which is how
        # xfdesktop names them (the monitor is its RandR/connector name, e.g. eDP-1).
        monitors = self._monitors()
        workspaces = self._workspace_count()
        for monitor in monitors:
            for number in range(workspaces):
                prop = (
                    f"/backdrop/screen0/monitor{monitor}/workspace{number}/last-image"
                )
                self.run(
                    ["xfconf-query", "-c", "xfce4-desktop", "-p", prop]
                    + ["--create", "-t", "string", "-s", str(path)]
                )

    def _monitors(self) -> list[str]:
        hint = (
            "Could not find the XFCE wallpaper settings. Pick a wallpaper once in "
            "Settings > Desktop to create them, or install 'xrandr' so "
            "they can be created automatically."
        )
        if shutil.which("xrandr") is None:
            raise WallpaperError(hint)
        lines = self.run(["xrandr", "--listmonitors"]).stdout.splitlines()[1:]
        # " 0: +*eDP-1 1920/344x1080/194+0+0  eDP-1": the name is the last word
        monitors = [line.split()[-1] for line in lines if line.strip()]
        if not monitors:
            raise WallpaperError(hint)
        return monitors

    def _workspace_count(self) -> int:
        result = self.run(
            ["xfconf-query", "-c", "xfwm4", "-p", "/general/workspace_count"],
            check=False,
        )
        try:
            return min(max(int(result.stdout.strip()), 1), 64)
        except ValueError:
            return 4  # xfwm4's default when the setting does not exist
