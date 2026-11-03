"""What the program remembers about the wallpapers it set itself.

The image that is set now, and the ones before it. They work like a stack: `back`
takes the newest one. The image that is set now is not on the stack.

Nothing in here reads files or touches the desktop.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

HISTORY_LIMIT = 5  # how many previous images `pbc back` can walk through


@dataclass
class State:
    current: str | None = None
    history: list[str] = field(default_factory=list)  # previous images, oldest first

    def record(self, image: str) -> None:
        """An image was set. The one it replaces goes on the history."""
        if self.current and self.current != image:
            self.history.append(self.current)
            del self.history[:-HISTORY_LIMIT]
        self.current = image

    def go_back(self, exists: Callable[[str], bool]) -> str | None:
        """Take the newest previous image that still exists and make it the current one.

        Images that are gone are dropped. Returns None when there is nothing to go back to.
        """
        while self.history and not exists(self.history[-1]):
            self.history.pop()
        if not self.history:
            return None
        self.current = self.history.pop()
        return self.current
