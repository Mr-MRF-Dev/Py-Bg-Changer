"""Command line interface."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from . import __version__, config
from .wallpaper import WallpaperError, set_wallpaper

COMMANDS = {"set", "list", "add", "remove", "rm", "path"}


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
            "  pbc                                  set the one named 'default'"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p = sub.add_parser("set", help="set the wallpaper (this is the default command)")
    p.add_argument("target", nargs="?", default="default",
                   help="a saved name or a path to an image (default: 'default')")

    sub.add_parser("list", help="show saved wallpapers")

    p = sub.add_parser("add", help="save an image under a name")
    p.add_argument("name")
    p.add_argument("path")

    p = sub.add_parser("remove", aliases=["rm"], help="forget a saved name")
    p.add_argument("name")

    sub.add_parser("path", help="print where the config file lives")
    return parser


def _error(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def cmd_set(target: str) -> int:
    wallpapers = config.load()

    if target in wallpapers:
        image = Path(wallpapers[target]).expanduser()
        label = f"'{target}'"
    elif Path(target).expanduser().is_file():
        image = Path(target).expanduser()
        label = str(image)
    else:
        if not wallpapers:
            return _error(
                f"Unknown wallpaper: '{target}'\n"
                "Nothing is saved yet. Save one with:  pbc add NAME IMAGE\n"
                "or pass an image path directly:       pbc IMAGE"
            )
        message = f"Unknown wallpaper: '{target}'"
        close = difflib.get_close_matches(target, wallpapers, n=1)
        if close:
            message += f"\nDid you mean '{close[0]}'?"
        message += f"\nAvailable: {', '.join(wallpapers)}"
        return _error(message)

    if not image.is_file():
        return _error(f"File not found: {image}")

    set_wallpaper(image)
    print(f"Wallpaper set to {label}")
    return 0


def cmd_list() -> int:
    wallpapers = config.load()
    if not wallpapers:
        print("Nothing saved yet. Save one with:  pbc add NAME IMAGE")
        return 0
    width = max(len(name) for name in wallpapers)
    for name, path in wallpapers.items():
        note = "" if Path(path).expanduser().is_file() else "  (missing)"
        print(f"{name:<{width}}  {path}{note}")
    return 0


def cmd_add(name: str, path: str) -> int:
    image = Path(path).expanduser().resolve()
    if not image.is_file():
        return _error(f"File not found: {image}")
    wallpapers = config.load()
    wallpapers[name] = str(image)
    config.save(wallpapers)
    print(f"Saved '{name}' -> {image}")
    return 0


def cmd_remove(name: str) -> int:
    wallpapers = config.load()
    if name not in wallpapers:
        return _error(f"Unknown wallpaper: '{name}'")
    del wallpapers[name]
    config.save(wallpapers)
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
            return cmd_add(args.name, args.path)
        if args.command in ("remove", "rm"):
            return cmd_remove(args.name)
        if args.command == "path":
            print(config.config_path())
            return 0
    except (config.ConfigError, WallpaperError) as exc:
        return _error(str(exc))
    return 0
