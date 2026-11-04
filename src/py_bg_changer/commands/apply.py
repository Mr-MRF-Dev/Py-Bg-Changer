"""Commands that change the wallpaper: set, random and back."""

from __future__ import annotations

import random
from pathlib import Path

from .. import config
from ..errors import ConfigError, UserError
from ..library import Library, resolved_path
from ..wallpaper import set_wallpaper
from .registry import arg, command


def _remember(image: Path) -> None:
    """Note which image was set last, so `pbc random` and `pbc back` know about it."""
    try:
        state = config.load_state()
        state.record(str(resolved_path(image)))
        config.save_state(state)
    except (OSError, ConfigError):
        pass  # only a convenience, never worth failing for


def _set_saved(library: Library, name: str) -> None:
    """Set the image saved under `name` (which has to be in the library)."""
    image = Path(library.wallpapers[name]).expanduser()
    if not image.is_file():
        raise UserError(
            f"File not found: {image}\nAdd it again with:  pbc add {name} IMAGE"
        )
    set_wallpaper(image)
    _remember(image)
    print(f"Wallpaper set to '{name}'")


@command(
    "set",
    help="set the wallpaper (this is the default command)",
    args=(
        arg(
            "target",
            nargs="?",
            help="a saved name or an alias (omit it to use the default)",
        ),
    ),
    examples=(
        ("pbc night", "set it by name or alias"),
        ("pbc", "set the default wallpaper"),
    ),
)
def cmd_set(target: str | None) -> None:
    library = config.load_library()

    if target is None:
        target = library.default_name()
        if target is None:
            if not library.wallpapers:
                raise UserError(
                    "Nothing is saved yet. Save one with:  pbc add NAME IMAGE --default"
                )
            raise UserError(
                "No default wallpaper is set. Choose one with:  pbc default NAME\n"
                f"Available: {library.labels()}"
            )

    saved = library.resolve(target)
    if saved is None:
        if Path(target).expanduser().is_file():
            raise UserError(
                f"'{target}' is an image file, not a saved name.\n"
                f"Save it first with:  pbc add NAME {target}"
            )
        raise library.unknown(target)
    _set_saved(library, saved)


@command(
    "random",
    help="set a random saved wallpaper",
    examples=(("pbc random", "set a random saved wallpaper"),),
)
def cmd_random() -> None:
    library = config.load_library()
    if not library.wallpapers:
        raise UserError("Nothing is saved yet. Save one with:  pbc add NAME IMAGE")

    # One entry per image (two names can share one file); missing files are skipped.
    usable: dict[Path, str] = {}
    for name, path in library.wallpapers.items():
        image = resolved_path(path)
        if image.is_file():
            usable.setdefault(image, name)
    if not usable:
        raise UserError(
            "None of the saved images exist any more. "
            "Add them again with:  pbc add NAME IMAGE"
        )

    # Avoid repeating the wallpaper that is set right now (if there is a choice).
    current = config.load_state().current
    others = [
        image for image in usable if current is None or image != resolved_path(current)
    ]
    _set_saved(library, usable[random.choice(others or list(usable))])


@command(
    "back",
    help="go back to the previous wallpaper",
    examples=(("pbc back", "go back to the previous wallpaper"),),
)
def cmd_back() -> None:
    state = config.load_state()
    previous = state.go_back(lambda path: Path(path).is_file())
    if previous is None:
        raise UserError("There is no previous wallpaper to go back to.")

    image = resolved_path(previous)
    set_wallpaper(image)
    state.current = str(image)
    try:
        config.save_state(state)
    except (OSError, ConfigError):
        pass  # the wallpaper is already set, so this is not worth failing for
    names = config.load_library().names_using(image)
    print(f"Wallpaper set back to {names[0] if names else image}")
