"""Commands that change what is saved: add, alias, rename, remove and default."""

from __future__ import annotations

from .. import cache, config
from ..errors import UserError
from ..library import resolved_path
from .registry import arg, command


@command(
    "add",
    help="save an image under a name",
    args=(
        arg("name"),
        arg("path"),
        arg(
            "-a",
            "--alias",
            action="append",
            dest="aliases",
            metavar="ALIAS",
            help="another name for the same image (repeat it for more)",
        ),
        arg(
            "-d",
            "--default",
            action="store_true",
            dest="make_default",
            help="also make it the default wallpaper",
        ),
    ),
    examples=(
        ("pbc add night ~/Pictures/night.jpg", "save an image under a name"),
        ("pbc add night img.jpg -a n -a dark", "...with extra names (aliases)"),
    ),
)
def cmd_add(
    name: str, path: str, make_default: bool, aliases: list[str] | None
) -> None:
    source = resolved_path(path)
    if not source.is_file():
        raise UserError(f"File not found: {source}")

    library = config.load_library()
    extra = library.check_new(name, aliases or [])  # before anything is copied

    try:
        stored = cache.store(source)
    except OSError as exc:
        raise UserError(f"Could not copy {source}: {exc}") from exc

    previous = library.add(name, str(stored), extra)
    if make_default:
        library.choose_default(name)
    config.save_library(library)
    if previous is not None:
        cache.release(previous, library.wallpapers)

    print(f"Saved '{name}' -> {stored}")
    if extra:
        print(f"Aliases: {', '.join(extra)}")
    if make_default:
        print(f"'{name}' is now the default wallpaper")


@command(
    "alias",
    help="give a saved wallpaper extra names",
    args=(
        arg("name", help="a saved name (or one of its aliases)"),
        arg("aliases", nargs="+", metavar="ALIAS"),
    ),
    examples=(("pbc alias night moon", "add more aliases later"),),
)
def cmd_alias(name: str, aliases: list[str]) -> None:
    library = config.load_library()
    real, added = library.add_aliases(name, aliases)
    if not added:
        print(f"'{real}' already has those aliases")
        return
    config.save_library(library)
    print(f"'{real}' is now also called: {', '.join(added)}")


@command(
    "rename",
    help="rename a saved wallpaper or an alias",
    args=(arg("old", help="a saved name or an alias"), arg("new")),
    examples=(("pbc rename night midnight", "rename a wallpaper or an alias"),),
)
def cmd_rename(old: str, new: str) -> None:
    library = config.load_library()
    kind = library.kind_of(old)
    if kind is None:
        raise library.unknown(old)
    if new == old:
        print(f"'{old}' is already called that")
        return
    library.rename(old, new)
    config.save_library(library)
    what = f"'{old}'" if kind == "wallpaper" else f"alias '{old}'"
    print(f"Renamed {what} to '{new}'")


@command(
    "remove",
    help="forget a saved name or alias",
    aliases=("rm",),
    args=(arg("name"),),
)
def cmd_remove(name: str) -> None:
    library = config.load_library()
    kind = library.kind_of(name)

    if kind == "wallpaper":
        image, gone = library.remove_wallpaper(name)
        config.save_library(library)
        cache.release(image, library.wallpapers)
        message = f"Removed '{name}'"
        if gone:
            message += f" (and its aliases: {', '.join(gone)})"
        print(message)
    elif kind == "alias":
        target = library.remove_alias(name)
        config.save_library(library)
        print(f"Removed alias '{name}' (the wallpaper '{target}' is still saved)")
    else:
        raise UserError(f"Unknown wallpaper: '{name}'")


@command(
    "default",
    help="choose the wallpaper that a plain 'pbc' sets",
    args=(
        arg(
            "name",
            nargs="?",
            help="a saved name or alias (omit it to show the default)",
        ),
    ),
    examples=(("pbc default night", "choose what a plain 'pbc' sets"),),
)
def cmd_default(name: str | None) -> None:
    library = config.load_library()
    if name is None:
        chosen = library.chosen_default()
        print(
            chosen if chosen else "No default set. Choose one with:  pbc default NAME"
        )
        return
    resolved = library.choose_default(name)
    config.save_library(library)
    print(f"'{resolved}' is now the default wallpaper")
