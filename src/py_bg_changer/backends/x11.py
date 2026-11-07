"""Any other desktop on X11 (i3, bspwm, ...), with feh or nitrogen."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..errors import WallpaperError
from .base import Backend, Environment


class X11Fallback(Backend):
    """The catch-all: it fits every Linux desktop that nothing else recognised.

    feh and nitrogen only draw on X11. On Wayland they would run without error and
    change nothing, so this one does not fit there.
    """

    name = "fallback (feh or nitrogen)"
    tools = ("feh", "nitrogen")
    any_of = True

    @classmethod
    def matches(cls, env: Environment) -> bool:
        return env.system == "Linux" and env.session != "wayland"

    def set(self, path: Path) -> None:
        for cmd in (
            ["feh", "--bg-fill", str(path)],
            ["nitrogen", "--set-zoom-fill", "--save", str(path)],
        ):
            if shutil.which(cmd[0]):
                self.run(cmd)
                return
        raise WallpaperError(
            f"Could not detect your desktop environment ({self.env.describe()}).\n"
            "Install 'feh' (or 'nitrogen') and try again."
        )
