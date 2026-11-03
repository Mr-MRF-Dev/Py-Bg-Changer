"""The saved wallpapers, their aliases and the chosen default.

`Library` keeps all of it in one object, together with the rules: a name cannot also
be an alias, an alias belongs to one wallpaper, removing a wallpaper takes its aliases
and the default with it, and so on. A command loads the library once, changes it and
saves it once, so the file is never left half updated.

Nothing in here prints, reads files or touches the desktop.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path

from .errors import UserError


def resolved_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


@dataclass
class Library:
    wallpapers: dict[str, str] = field(default_factory=dict)  # name -> image path
    aliases: dict[str, str] = field(default_factory=dict)  # alias -> name
    default: str | None = None  # a name or an alias, as it is written in the config

    # --- looking things up -----------------------------------------------------

    def kind_of(self, name: str) -> str | None:
        """ "wallpaper" or "alias" for a name that is taken, None for a free one."""
        if name in self.wallpapers:
            return "wallpaper"
        if name in self.aliases:
            return "alias"
        return None

    def resolve(self, name: str) -> str | None:
        """The saved wallpaper a name or alias stands for, or None."""
        if name in self.wallpapers:
            return name
        target = self.aliases.get(name)
        return target if target in self.wallpapers else None

    def aliases_of(self, name: str) -> list[str]:
        return [alias for alias, target in self.aliases.items() if target == name]

    def label(self, name: str) -> str:
        """The name with its aliases, e.g. "night (n, dark)"."""
        extra = self.aliases_of(name)
        return f"{name} ({', '.join(extra)})" if extra else name

    def labels(self) -> str:
        return ", ".join(self.label(name) for name in self.wallpapers)

    def chosen_default(self) -> str | None:
        """The wallpaper that the chosen default stands for, if it still exists."""
        return self.resolve(self.default) if self.default else None

    def default_name(self) -> str | None:
        """The wallpaper that a plain `pbc` sets."""
        chosen = self.chosen_default()
        if chosen:
            return chosen
        # Configs from the original bg.py use a wallpaper literally named "default".
        return "default" if "default" in self.wallpapers else None

    def names_using(self, image: Path) -> list[str]:
        """The saved wallpapers (with their aliases) that use this image."""
        return [
            self.label(name)
            for name, path in self.wallpapers.items()
            if resolved_path(path) == image
        ]

    def unknown(self, name: str) -> UserError:
        """The error for a name that is not saved, with a hint about what to use."""
        message = f"Unknown wallpaper: '{name}'"
        close = difflib.get_close_matches(name, [*self.wallpapers, *self.aliases], n=1)
        if close:
            message += f"\nDid you mean '{close[0]}'?"
        if self.wallpapers:
            message += f"\nAvailable: {self.labels()}"
        else:
            message += "\nNothing is saved yet. Save one with:  pbc add NAME IMAGE"
        return UserError(message)

    # --- changing things (they raise UserError when a rule is broken) --------------

    def _check_aliases(self, owner: str, requested: list[str]) -> None:
        for alias in requested:
            if alias == owner:
                raise UserError(f"'{alias}' is already the name of this wallpaper.")
            if alias in self.wallpapers:
                raise UserError(f"'{alias}' is already a saved wallpaper name.")
            if alias in self.aliases and self.aliases[alias] != owner:
                raise UserError(
                    f"'{alias}' is already an alias of '{self.aliases[alias]}'."
                )

    def check_new(self, name: str, alias_names: list[str]) -> list[str]:
        """Check that `name` can be saved with these aliases, before anything is done.

        Returns the aliases without repeats, to pass to `add`.
        """
        if name in self.aliases:
            raise UserError(
                f"'{name}' is already an alias of '{self.aliases[name]}'.\n"
                f"Remove the alias first with:  pbc remove {name}"
            )
        requested = list(dict.fromkeys(alias_names))
        self._check_aliases(name, requested)
        return requested

    def add(self, name: str, image: str, aliases: list[str]) -> str | None:
        """Save a wallpaper (or replace the image of one). Returns the image it replaced."""
        previous = self.wallpapers.get(name)
        self.wallpapers[name] = image
        for alias in aliases:
            self.aliases[alias] = name
        return previous

    def add_aliases(self, name: str, new_aliases: list[str]) -> tuple[str, list[str]]:
        """Give a saved wallpaper (by name or alias) more aliases.

        Returns the wallpaper's name and the aliases that were really new.
        """
        real = self.resolve(name)
        if real is None:
            raise self.unknown(name)
        requested = list(dict.fromkeys(new_aliases))
        self._check_aliases(real, requested)
        added = [alias for alias in requested if alias not in self.aliases]
        for alias in added:
            self.aliases[alias] = real
        return real, added

    def rename(self, old: str, new: str) -> None:
        """Rename a wallpaper or an alias. A wallpaper keeps its aliases and its place
        as the default."""
        if self.kind_of(old) is None:
            raise self.unknown(old)
        if new in self.wallpapers:
            raise UserError(f"'{new}' is already a saved wallpaper name.")
        if new in self.aliases:
            raise UserError(f"'{new}' is already an alias of '{self.aliases[new]}'.")

        # Rebuild the dicts so the renamed entry keeps its place in the list.
        if old in self.wallpapers:
            self.wallpapers = {
                (new if name == old else name): image
                for name, image in self.wallpapers.items()
            }
            self.aliases = {
                alias: (new if target == old else target)
                for alias, target in self.aliases.items()
            }
        else:
            self.aliases = {
                (new if alias == old else alias): target
                for alias, target in self.aliases.items()
            }
        if self.default == old:
            self.default = new

    def remove_wallpaper(self, name: str) -> tuple[str, list[str]]:
        """Forget a wallpaper, its aliases and (if it was) the default.

        Returns the image it used and the aliases that went with it.
        """
        image = self.wallpapers.pop(name)
        gone = self.aliases_of(name)
        for alias in gone:
            del self.aliases[alias]
        if self.default == name:
            self.default = None
        return image, gone

    def remove_alias(self, name: str) -> str:
        """Forget an alias. Returns the wallpaper it pointed to."""
        return self.aliases.pop(name)

    def choose_default(self, name: str) -> str:
        """Make a wallpaper (by name or alias) the default. Returns its name."""
        real = self.resolve(name)
        if real is None:
            raise self.unknown(name)
        self.default = real
        return real
