"""Command line interface."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import NoReturn

from . import __version__, cache, config, doctor
from .errors import ConfigError, PbcError, UsageError, UserError
from .library import Library, resolved_path
from .wallpaper import set_wallpaper

COMMANDS = {
    "set",
    "list",
    "ls",
    "add",
    "alias",
    "rename",
    "remove",
    "rm",
    "default",
    "random",
    "current",
    "back",
    "doctor",
    "path",
}


class _Parser(argparse.ArgumentParser):
    """argparse, but a wrong command line is an error to raise, not a reason to exit."""

    def error(self, message: str) -> NoReturn:
        raise UsageError(f"{self.format_usage()}{self.prog}: error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="py-bg-changer",
        description="Change your desktop wallpaper from the command line.",
        epilog=(
            "'pbc' is a short alias for 'py-bg-changer'.\n\n"
            "examples:\n"
            "  pbc add night ~/Pictures/night.jpg   save an image under a name\n"
            "  pbc add night img.jpg -a n -a dark   ...with extra names (aliases)\n"
            "  pbc alias night moon                 add more aliases later\n"
            "  pbc rename night midnight            rename a wallpaper or an alias\n"
            "  pbc default night                    choose what a plain 'pbc' sets\n"
            "  pbc night                            set it by name or alias\n"
            "  pbc random                           set a random saved wallpaper\n"
            "  pbc current                          show which wallpaper is set now\n"
            "  pbc back                             go back to the previous wallpaper\n"
            "  pbc doctor                           check your setup if nothing changes\n"
            "  pbc                                  set the default wallpaper"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p = sub.add_parser("set", help="set the wallpaper (this is the default command)")
    p.add_argument(
        "target",
        nargs="?",
        help="a saved name or an alias (omit it to use the default)",
    )

    sub.add_parser(
        "list", aliases=["ls"], help="show saved wallpapers (* marks the default)"
    )

    sub.add_parser("random", help="set a random saved wallpaper")
    sub.add_parser("current", help="show which wallpaper is set now")
    sub.add_parser("back", help="go back to the previous wallpaper")
    sub.add_parser("doctor", help="check your setup if a wallpaper does not change")

    p = sub.add_parser("add", help="save an image under a name")
    p.add_argument("name")
    p.add_argument("path")
    p.add_argument(
        "-a",
        "--alias",
        action="append",
        dest="aliases",
        metavar="ALIAS",
        help="another name for the same image (repeat it for more)",
    )
    p.add_argument(
        "-d",
        "--default",
        action="store_true",
        dest="make_default",
        help="also make it the default wallpaper",
    )

    p = sub.add_parser("alias", help="give a saved wallpaper extra names")
    p.add_argument("name", help="a saved name (or one of its aliases)")
    p.add_argument("aliases", nargs="+", metavar="ALIAS")

    p = sub.add_parser("rename", help="rename a saved wallpaper or an alias")
    p.add_argument("old", help="a saved name or an alias")
    p.add_argument("new")

    p = sub.add_parser("default", help="choose the wallpaper that a plain 'pbc' sets")
    p.add_argument(
        "name", nargs="?", help="a saved name or alias (omit it to show the default)"
    )

    p = sub.add_parser("remove", aliases=["rm"], help="forget a saved name or alias")
    p.add_argument("name")

    sub.add_parser("path", help="print where the config file lives")
    return parser


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


def cmd_current() -> None:
    current = config.load_state().current
    if current is None:
        print("Nothing has been set by py-bg-changer yet.")
        return
    image = resolved_path(current)
    names = config.load_library().names_using(image)
    note = "" if image.is_file() else "  (missing)"
    print(f"{', '.join(names)}  {image}{note}" if names else f"{image}{note}")


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


def cmd_add(
    name: str, path: str, make_default: bool, alias_names: list[str] | None
) -> None:
    source = resolved_path(path)
    if not source.is_file():
        raise UserError(f"File not found: {source}")

    library = config.load_library()
    aliases = library.check_new(name, alias_names or [])  # before anything is copied

    try:
        stored = cache.store(source)
    except OSError as exc:
        raise UserError(f"Could not copy {source}: {exc}") from exc

    previous = library.add(name, str(stored), aliases)
    if make_default:
        library.choose_default(name)
    config.save_library(library)
    if previous is not None:
        cache.release(previous, library.wallpapers)

    print(f"Saved '{name}' -> {stored}")
    if aliases:
        print(f"Aliases: {', '.join(aliases)}")
    if make_default:
        print(f"'{name}' is now the default wallpaper")


def cmd_alias(name: str, new_aliases: list[str]) -> None:
    library = config.load_library()
    real, added = library.add_aliases(name, new_aliases)
    if not added:
        print(f"'{real}' already has those aliases")
        return
    config.save_library(library)
    print(f"'{real}' is now also called: {', '.join(added)}")


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


def run(argv: list[str] | None = None) -> int:
    """Run one command and return its exit code.

    Problems are raised as `PbcError`; `main` shows them in the terminal.
    """
    args_list = list(sys.argv[1:] if argv is None else argv)

    # "pbc night" is shorthand for "pbc set night".
    if not args_list or (
        args_list[0] not in COMMANDS and not args_list[0].startswith("-")
    ):
        args_list.insert(0, "set")

    args = build_parser().parse_args(args_list)

    if args.command == "set":
        cmd_set(args.target)
    elif args.command in ("list", "ls"):
        cmd_list()
    elif args.command == "add":
        cmd_add(args.name, args.path, args.make_default, args.aliases)
    elif args.command == "random":
        cmd_random()
    elif args.command == "current":
        cmd_current()
    elif args.command == "back":
        cmd_back()
    elif args.command == "doctor":
        return doctor.run()
    elif args.command == "alias":
        cmd_alias(args.name, args.aliases)
    elif args.command == "rename":
        cmd_rename(args.old, args.new)
    elif args.command == "default":
        cmd_default(args.name)
    elif args.command in ("remove", "rm"):
        cmd_remove(args.name)
    elif args.command == "path":
        print(config.config_path())
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except PbcError as exc:
        print(exc, file=sys.stderr)
        return exc.exit_code
