"""What every way of setting the wallpaper has in common."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, NamedTuple

from ..errors import WallpaperError


@dataclass(frozen=True)
class Environment:
    """What a backend needs to know about the machine to say if it fits."""

    system: str  # platform.system(): "Windows", "Darwin" or "Linux"
    current_desktop: str = ""  # XDG_CURRENT_DESKTOP, as it is
    desktop_session: str = ""  # DESKTOP_SESSION, as it is
    session_type: str = ""  # XDG_SESSION_TYPE, as it is

    @classmethod
    def detect(cls) -> Environment:
        return cls(
            system=platform.system(),
            current_desktop=os.environ.get("XDG_CURRENT_DESKTOP", ""),
            desktop_session=os.environ.get("DESKTOP_SESSION", ""),
            session_type=os.environ.get("XDG_SESSION_TYPE", ""),
        )

    @property
    def desktop(self) -> str:
        """The desktop environment as one lowercase string, e.g. "ubuntu:gnome"."""
        return ":".join(
            filter(None, [self.current_desktop, self.desktop_session])
        ).lower()

    @property
    def session(self) -> str:
        """The session type in lowercase: "x11", "wayland" or empty."""
        return self.session_type.lower()

    def describe(self) -> str:
        """The values above as they are, to show in a message."""
        values = (
            ("XDG_CURRENT_DESKTOP", self.current_desktop),
            ("DESKTOP_SESSION", self.desktop_session),
            ("XDG_SESSION_TYPE", self.session_type),
        )
        return ", ".join(f"{name}={value!r}" for name, value in values)


class BackendInfo(NamedTuple):
    """What a backend needs, to show in `pbc doctor`."""

    name: str
    tools: tuple[str, ...] = ()  # commands it needs
    any_of: bool = False  # True when one of the tools is enough
    optional: tuple[str, ...] = ()  # commands that are only sometimes needed
    note: str = ""
    supported: bool = True


class Backend(ABC):
    """One way of setting the wallpaper.

    To support a new desktop, write a subclass and add it to `BACKENDS` in
    `backends/__init__.py`.
    """

    name: ClassVar[str]
    tools: ClassVar[tuple[str, ...]] = ()
    any_of: ClassVar[bool] = False
    optional: ClassVar[tuple[str, ...]] = ()
    note: ClassVar[str] = ""

    def __init__(self, env: Environment) -> None:
        self.env = env

    @classmethod
    @abstractmethod
    def matches(cls, env: Environment) -> bool:
        """Is this the way to set the wallpaper on this machine?"""

    @abstractmethod
    def set(self, path: Path) -> None:
        """Set this image (an absolute path) as the wallpaper."""

    @classmethod
    def info(cls) -> BackendInfo:
        return BackendInfo(cls.name, cls.tools, cls.any_of, cls.optional, cls.note)

    def run(
        self, cmd: list[str], *, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        """Run a command of the system. Tests replace this one to record commands."""
        if shutil.which(cmd[0]) is None:
            raise WallpaperError(f"'{cmd[0]}' was not found on this system.")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if check and result.returncode != 0:
            detail = result.stderr.strip() or f"exit code {result.returncode}"
            raise WallpaperError(f"{cmd[0]} failed: {detail}")
        return result


class LinuxDesktop(Backend):
    """A Linux desktop that is recognised by a word in XDG_CURRENT_DESKTOP."""

    keywords: ClassVar[tuple[str, ...]]

    @classmethod
    def matches(cls, env: Environment) -> bool:
        return env.system == "Linux" and any(
            keyword in env.desktop for keyword in cls.keywords
        )
