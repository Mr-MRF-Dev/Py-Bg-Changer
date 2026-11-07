"""Desktops that keep the wallpaper in gsettings: Cinnamon, MATE and GNOME."""

from __future__ import annotations

from pathlib import Path

from .base import LinuxDesktop


class Cinnamon(LinuxDesktop):
    name = "cinnamon"
    tools = ("gsettings",)
    keywords = ("cinnamon",)

    def set(self, path: Path) -> None:
        self.run(
            [
                "gsettings",
                "set",
                "org.cinnamon.desktop.background",
                "picture-uri",
                path.as_uri(),
            ]
        )


class Mate(LinuxDesktop):
    name = "mate"
    tools = ("gsettings",)
    keywords = ("mate",)

    def set(self, path: Path) -> None:
        self.run(
            ["gsettings", "set", "org.mate.background", "picture-filename", str(path)]
        )


class Gnome(LinuxDesktop):
    """GNOME and the desktops that are built on it."""

    name = "gnome"
    tools = ("gsettings",)
    keywords = ("gnome", "budgie", "unity", "pantheon")

    def set(self, path: Path) -> None:
        uri = path.as_uri()
        self.run(
            ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri]
        )
        # Newer GNOME has a separate key for dark mode; older versions don't.
        self.run(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri-dark",
                uri,
            ],
            check=False,
        )
