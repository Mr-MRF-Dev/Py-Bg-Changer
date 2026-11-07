"""Windows."""

from __future__ import annotations

from pathlib import Path

from ..errors import WallpaperError
from .base import Backend, Environment


class Windows(Backend):
    name = "windows (SystemParametersInfoW)"

    @classmethod
    def matches(cls, env: Environment) -> bool:
        return env.system == "Windows"

    def set(self, path: Path) -> None:
        import ctypes

        SPI_SETDESKWALLPAPER = 0x0014
        SPIF_UPDATEINIFILE = 0x01
        SPIF_SENDCHANGE = 0x02
        # `windll` only exists on Windows, so type checkers on other systems do not know it.
        ok = ctypes.windll.user32.SystemParametersInfoW(  # type: ignore[attr-defined,unused-ignore]
            SPI_SETDESKWALLPAPER, 0, str(path), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )
        if not ok:
            raise WallpaperError("Windows refused to change the wallpaper.")
