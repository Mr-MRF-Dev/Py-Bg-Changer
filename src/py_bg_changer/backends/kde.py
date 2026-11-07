"""KDE Plasma."""

from __future__ import annotations

from pathlib import Path

from .base import LinuxDesktop


class Kde(LinuxDesktop):
    name = "kde"
    tools = ("plasma-apply-wallpaperimage",)
    keywords = ("kde", "plasma")

    def set(self, path: Path) -> None:
        self.run(["plasma-apply-wallpaperimage", str(path)])
