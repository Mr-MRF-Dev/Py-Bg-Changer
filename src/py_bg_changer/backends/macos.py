"""macOS."""

from __future__ import annotations

from pathlib import Path

from .base import Backend, Environment


class MacOS(Backend):
    name = "macos (osascript)"
    tools = ("osascript",)

    @classmethod
    def matches(cls, env: Environment) -> bool:
        return env.system == "Darwin"

    def set(self, path: Path) -> None:
        escaped = str(path).replace("\\", "\\\\").replace('"', '\\"')
        script = (
            'tell application "System Events" to tell every desktop '
            f'to set picture to "{escaped}"'
        )
        self.run(["osascript", "-e", script])
