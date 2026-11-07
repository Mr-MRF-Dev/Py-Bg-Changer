"""Sway."""

from __future__ import annotations

from pathlib import Path

from .base import LinuxDesktop


class Sway(LinuxDesktop):
    name = "sway"
    tools = ("swaymsg",)
    keywords = ("sway",)

    def set(self, path: Path) -> None:
        self.run(["swaymsg", "output", "*", "bg", str(path), "fill"])
