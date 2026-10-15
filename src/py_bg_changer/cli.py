"""Command line interface."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from . import __version__, cache, config
from .wallpaper import WallpaperError, set_wallpaper

COMMANDS = {"set", "list", "add", "remove", "rm", "default", "path"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="py-bg-changer",
        description="Change your desktop wallpaper from the command line.",
        epilog=(
            "'pbc' is a short alias for 'py-bg-changer'.\n\n"
            "examples:\n"
            "  pbc add night ~/Pictures/night.jpg   save an image under a name\n"
            "  pbc night                            set it by name\n"
            "  pbc ~/Pictures/any.png               set any image directly\n"
            "  pbc default night                    choose what a plain 'pbc' sets\n"
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
        help="a saved name or a path to an image (omit it to use the default)",
    )

    sub.add_parser("list", help="show saved wallpapers (* marks the default)")

    p = sub.add_parser("add", help="save an image under a name")
    p.add_argument("name")
    p.add_argument("path")
    p.add_argument(
        "-d",
        "--default",
        action="store_true",
        dest="make_default",
        help="also make it the default wallpaper",
    )

    p = sub.add_parser("default", help="choose the wallpaper that a plain 'pbc' sets")
    p.add_argument("name", nargs="?", help="a saved name (omit it to show the default)")

    p = sub.add_parser("remove", aliases=["rm"], help="forget a saved name")
    p.add_argument("name")

    sub.add_parser("path", help="print where the config file lives")
    return parser


def _error(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _unknown(target: str, wallpapers: dict[str, str]) -> int:
    message = f"Unknown wallpaper: '{target}'"
    close = difflib.get_close_matches(target, wallpapers, n=1)
    if close:
        message += f"\nDid you mean '{close[0]}'?"
    if wallpapers:
        message += f"\nAvailable: {', '.join(wallpapers)}"
    else:
        message += "\nNothing is saved yet. Save one with:  pbc add NAME IMAGE"
    return _error(message)


def _default_name(wallpapers: dict[str, str]) -> str | None:
    chosen = config.get_default()
    if chosen in wallpapers:
        return chosen
    # Configs from the original bg.py use a wallpaper literally named "default".
    if "default" in wallpapers:
        return "default"
    return None


def cmd_set(target: str | None) -> int:
    wallpapers = config.load()

    if target is None:
        target = _default_name(wallpapers)
        if target is None:
            if not wallpapers:
                return _error(
                    "Nothing is saved yet. Save one with:  pbc add NAME IMAGE --default"
                )
            return _error(
                "No default wallpaper is set. Choose one with:  pbc default NAME\n"
                f"Available: {', '.join(wallpapers)}"
            )

    saved = target in wallpapers
    if saved:
        image = Path(wallpapers[target]).expanduser()
        label = f"'{target}'"
    elif Path(target).expanduser().is_file():
        image = Path(target).expanduser()
        label = str(image)
    else:
        return _unknown(target, wallpapers)

    if not image.is_file():
        message = f"File not found: {image}"
        if saved:
            message += f"\nAdd it again with:  pbc add {target} IMAGE"
        return _error(message)

    set_wallpaper(image)
    print(f"Wallpaper set to {label}")
    return 0


def cmd_list() -> int:
    wallpapers = config.load()
    if not wallpapers:
        print("Nothing saved yet. Save one with:  pbc add NAME IMAGE")
        return 0
    default = _default_name(wallpapers)
    width = max(len(name) for name in wallpapers)
    for name, path in wallpapers.items():
        mark = "*" if name == default else " "
        note = "" if Path(path).expanduser().is_file() else "  (missing)"
        print(f"{mark} {name:<{width}}  {path}{note}")
    return 0


def cmd_add(name: str, path: str, make_default: bool) -> int:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        return _error(f"File not found: {source}")
    try:
        stored = cache.store(source)
    except OSError as exc:
        return _error(f"Could not copy {source}: {exc}")

    wallpapers = config.load()
    previous = wallpapers.get(name)
    wallpapers[name] = str(stored)
    config.save(wallpapers)
    if previous is not None:
        cache.release(previous, wallpapers)

    print(f"Saved '{name}' -> {stored}")
    if make_default:
        config.set_default(name)
        print(f"'{name}' is now the default wallpaper")
    return 0


def cmd_default(name: str | None) -> int:
    wallpapers = config.load()
    if name is None:
        current = config.get_default()
        if current in wallpapers:
            print(current)
        else:
            print("No default set. Choose one with:  pbc default NAME")
        return 0
    if name not in wallpapers:
        return _unknown(name, wallpapers)
    config.set_default(name)
    print(f"'{name}' is now the default wallpaper")
    return 0


def cmd_remove(name: str) -> int:
    wallpapers = config.load()
    if name not in wallpapers:
        return _error(f"Unknown wallpaper: '{name}'")
    removed = wallpapers.pop(name)
    config.save(wallpapers)
    if config.get_default() == name:
        config.set_default(None)
    cache.release(removed, wallpapers)
    print(f"Removed '{name}'")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # "pbc night" is shorthand for "pbc set night".
    if not argv or (argv[0] not in COMMANDS and not argv[0].startswith("-")):
        argv.insert(0, "set")

    args = build_parser().parse_args(argv)

    try:
        if args.command == "set":
            return cmd_set(args.target)
        if args.command == "list":
            return cmd_list()
        if args.command == "add":
            return cmd_add(args.name, args.path, args.make_default)
        if args.command == "default":
            return cmd_default(args.name)
        if args.command in ("remove", "rm"):
            return cmd_remove(args.name)
        if args.command == "path":
            print(config.config_path())
            return 0
    except (config.ConfigError, WallpaperError) as exc:
        return _error(str(exc))
    return 0
