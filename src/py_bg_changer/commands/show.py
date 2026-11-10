"""Commands that only show something: current, list, doctor and path."""

from __future__ import annotations

from pathlib import Path

from .. import config, doctor
from ..library import resolved_path
from .registry import command


@command(
    "current",
    help="show which wallpaper is set now",
    examples=(("pbc current", "show which wallpaper is set now"),),
)
def cmd_current() -> None:
    current = config.load_state().current
    if current is None:
        print("Nothing has been set by py-bg-changer yet.")
        return
    image = resolved_path(current)
    names = config.load_library().names_using(image)
    note = "" if image.is_file() else "  (missing)"
    print(f"{', '.join(names)}  {image}{note}" if names else f"{image}{note}")


@command(
    "list",
    help="show saved wallpapers (* marks the default)",
    aliases=("ls",),
)
def cmd_list() -> None:
    library = config.load_library()
    if not library.wallpapers:
        print("Nothing saved yet. Save one with:  pbc add NAME IMAGE")
        return
    default = library.default_name()
    labels = {name: library.label(name) for name in library.wallpapers}
    width = max(len(label) for label in labels.values())
    for name, path in library.wallpapers.items():
        mark = "*" if name == default else " "
        note = "" if Path(path).expanduser().is_file() else "  (missing)"
        print(f"{mark} {labels[name]:<{width}}  {path}{note}")


@command(
    "doctor",
    help="check your setup if a wallpaper does not change",
    examples=(("pbc doctor", "check your setup if nothing changes"),),
    migrate=False,  # it checks the files itself, and has to work when they are broken
)
def cmd_doctor() -> int:
    return doctor.run()


@command("path", help="print where the config file lives", migrate=False)
def cmd_path() -> None:
    print(config.config_path())
