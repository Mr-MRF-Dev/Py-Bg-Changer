"""Command line interface."""

from __future__ import annotations

import argparse
import difflib
import random
import sys
from pathlib import Path

from . import __version__, cache, config
from .wallpaper import WallpaperError, set_wallpaper

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
    "path",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="py-bg-changer",
        description="Change your desktop wallpaper from the command line.",
        epilog=(
            "'pbc' is a short alias for 'py-bg-changer'.\n\n"
            "examples:\n"
            "  pbc add night ~/Pictures/night.jpg   save an image under a name\n"
            "  pbc add night img.jpg -a n -a dark   ...with extra names (aliases)\n"
            "  pbc alias night moon                 add more aliases later\n"
            "  pbc rename night midnight            rename a wallpaper or an alias\n"
            "  pbc night                            set it by name or alias\n"
            "  pbc ~/Pictures/any.png               set any image directly\n"
            "  pbc random                           set a random saved wallpaper\n"
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
        help="a saved name, an alias or a path to an image (omit it to use the default)",
    )

    sub.add_parser(
        "list", aliases=["ls"], help="show saved wallpapers (* marks the default)"
    )

    sub.add_parser("random", help="set a random saved wallpaper")

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


def _error(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _resolve(
    name: str, wallpapers: dict[str, str], aliases: dict[str, str]
) -> str | None:
    """The saved wallpaper a name or alias stands for, or None."""
    if name in wallpapers:
        return name
    target = aliases.get(name)
    return target if target in wallpapers else None


def _aliases_of(name: str, aliases: dict[str, str]) -> list[str]:
    return [alias for alias, target in aliases.items() if target == name]


def _label(name: str, aliases: dict[str, str]) -> str:
    extra = _aliases_of(name, aliases)
    return f"{name} ({', '.join(extra)})" if extra else name


def _check_aliases(
    owner: str,
    requested: list[str],
    wallpapers: dict[str, str],
    aliases: dict[str, str],
) -> str | None:
    """An error message if one of the aliases can't be used for `owner`."""
    for alias in requested:
        if alias == owner:
            return f"'{alias}' is already the name of this wallpaper."
        if alias in wallpapers:
            return f"'{alias}' is already a saved wallpaper name."
        if alias in aliases and aliases[alias] != owner:
            return f"'{alias}' is already an alias of '{aliases[alias]}'."
    return None


def _unknown(target: str, wallpapers: dict[str, str], aliases: dict[str, str]) -> int:
    message = f"Unknown wallpaper: '{target}'"
    close = difflib.get_close_matches(target, [*wallpapers, *aliases], n=1)
    if close:
        message += f"\nDid you mean '{close[0]}'?"
    if wallpapers:
        labels = ", ".join(_label(name, aliases) for name in wallpapers)
        message += f"\nAvailable: {labels}"
    else:
        message += "\nNothing is saved yet. Save one with:  pbc add NAME IMAGE"
    return _error(message)


def _default_name(wallpapers: dict[str, str], aliases: dict[str, str]) -> str | None:
    chosen = config.get_default()
    if chosen:
        resolved = _resolve(chosen, wallpapers, aliases)
        if resolved:
            return resolved
    # Configs from the original bg.py use a wallpaper literally named "default".
    if "default" in wallpapers:
        return "default"
    return None


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _remember(image: Path) -> None:
    """Note which image was set last, so `pbc random` can pick a different one."""
    try:
        config.set_current(str(_resolved(image)))
    except (OSError, config.ConfigError):
        pass  # only a convenience, never worth failing for


def cmd_set(target: str | None) -> int:
    wallpapers = config.load()
    aliases = config.load_aliases()

    if target is None:
        target = _default_name(wallpapers, aliases)
        if target is None:
            if not wallpapers:
                return _error(
                    "Nothing is saved yet. Save one with:  pbc add NAME IMAGE --default"
                )
            labels = ", ".join(_label(name, aliases) for name in wallpapers)
            return _error(
                "No default wallpaper is set. Choose one with:  pbc default NAME\n"
                f"Available: {labels}"
            )

    saved = _resolve(target, wallpapers, aliases)
    if saved is not None:
        image = Path(wallpapers[saved]).expanduser()
        label = f"'{saved}'"
    elif Path(target).expanduser().is_file():
        image = Path(target).expanduser()
        label = str(image)
    else:
        return _unknown(target, wallpapers, aliases)

    if not image.is_file():
        message = f"File not found: {image}"
        if saved is not None:
            message += f"\nAdd it again with:  pbc add {saved} IMAGE"
        return _error(message)

    set_wallpaper(image)
    _remember(image)
    print(f"Wallpaper set to {label}")
    return 0


def cmd_random() -> int:
    wallpapers = config.load()
    if not wallpapers:
        return _error("Nothing is saved yet. Save one with:  pbc add NAME IMAGE")

    # One entry per image (two names can share one file); missing files are skipped.
    usable: dict[Path, str] = {}
    for name, path in wallpapers.items():
        image = _resolved(path)
        if image.is_file():
            usable.setdefault(image, name)
    if not usable:
        return _error(
            "None of the saved images exist any more. "
            "Add them again with:  pbc add NAME IMAGE"
        )

    # Avoid repeating the wallpaper that is set right now (if there is a choice).
    current = config.get_current()
    others = [
        image for image in usable if current is None or image != _resolved(current)
    ]
    return cmd_set(usable[random.choice(others or list(usable))])


def cmd_list() -> int:
    wallpapers = config.load()
    aliases = config.load_aliases()
    if not wallpapers:
        print("Nothing saved yet. Save one with:  pbc add NAME IMAGE")
        return 0
    default = _default_name(wallpapers, aliases)
    labels = {name: _label(name, aliases) for name in wallpapers}
    width = max(len(label) for label in labels.values())
    for name, path in wallpapers.items():
        mark = "*" if name == default else " "
        note = "" if Path(path).expanduser().is_file() else "  (missing)"
        print(f"{mark} {labels[name]:<{width}}  {path}{note}")
    return 0


def cmd_add(
    name: str, path: str, make_default: bool, alias_names: list[str] | None
) -> int:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        return _error(f"File not found: {source}")

    wallpapers = config.load()
    aliases = config.load_aliases()
    if name in aliases:
        return _error(
            f"'{name}' is already an alias of '{aliases[name]}'.\n"
            f"Remove the alias first with:  pbc remove {name}"
        )
    requested = _dedupe(alias_names or [])
    problem = _check_aliases(name, requested, wallpapers, aliases)
    if problem:
        return _error(problem)

    try:
        stored = cache.store(source)
    except OSError as exc:
        return _error(f"Could not copy {source}: {exc}")

    previous = wallpapers.get(name)
    wallpapers[name] = str(stored)
    for alias in requested:
        aliases[alias] = name
    config.save(wallpapers, aliases)
    if previous is not None:
        cache.release(previous, wallpapers)

    print(f"Saved '{name}' -> {stored}")
    if requested:
        print(f"Aliases: {', '.join(requested)}")
    if make_default:
        config.set_default(name)
        print(f"'{name}' is now the default wallpaper")
    return 0


def cmd_alias(name: str, new_aliases: list[str]) -> int:
    wallpapers = config.load()
    aliases = config.load_aliases()
    real = _resolve(name, wallpapers, aliases)
    if real is None:
        return _unknown(name, wallpapers, aliases)

    requested = _dedupe(new_aliases)
    problem = _check_aliases(real, requested, wallpapers, aliases)
    if problem:
        return _error(problem)

    added = [alias for alias in requested if alias not in aliases]
    if not added:
        print(f"'{real}' already has those aliases")
        return 0
    for alias in added:
        aliases[alias] = real
    config.save(wallpapers, aliases)
    print(f"'{real}' is now also called: {', '.join(added)}")
    return 0


def cmd_rename(old: str, new: str) -> int:
    wallpapers = config.load()
    aliases = config.load_aliases()
    if old not in wallpapers and old not in aliases:
        return _unknown(old, wallpapers, aliases)
    if new == old:
        print(f"'{old}' is already called that")
        return 0
    if new in wallpapers:
        return _error(f"'{new}' is already a saved wallpaper name.")
    if new in aliases:
        return _error(f"'{new}' is already an alias of '{aliases[new]}'.")

    # Rebuild the dicts so the renamed entry keeps its place in the list.
    if old in wallpapers:
        wallpapers = {
            (new if name == old else name): path for name, path in wallpapers.items()
        }
        aliases = {
            alias: (new if target == old else target)
            for alias, target in aliases.items()
        }
        what = f"'{old}'"
    else:
        aliases = {
            (new if alias == old else alias): target
            for alias, target in aliases.items()
        }
        what = f"alias '{old}'"
    config.save(wallpapers, aliases)
    if config.get_default() == old:
        config.set_default(new)
    print(f"Renamed {what} to '{new}'")
    return 0


def cmd_default(name: str | None) -> int:
    wallpapers = config.load()
    aliases = config.load_aliases()
    if name is None:
        current = config.get_default()
        resolved = _resolve(current, wallpapers, aliases) if current else None
        if resolved:
            print(resolved)
        else:
            print("No default set. Choose one with:  pbc default NAME")
        return 0
    resolved = _resolve(name, wallpapers, aliases)
    if resolved is None:
        return _unknown(name, wallpapers, aliases)
    config.set_default(resolved)
    print(f"'{resolved}' is now the default wallpaper")
    return 0


def cmd_remove(name: str) -> int:
    wallpapers = config.load()
    aliases = config.load_aliases()

    if name in wallpapers:
        removed = wallpapers.pop(name)
        gone = _aliases_of(name, aliases)
        for alias in gone:
            del aliases[alias]
        config.save(wallpapers, aliases)
        if config.get_default() == name:
            config.set_default(None)
        cache.release(removed, wallpapers)
        message = f"Removed '{name}'"
        if gone:
            message += f" (and its aliases: {', '.join(gone)})"
        print(message)
        return 0

    if name in aliases:
        target = aliases.pop(name)
        config.save(wallpapers, aliases)
        print(f"Removed alias '{name}' (the wallpaper '{target}' is still saved)")
        return 0

    return _error(f"Unknown wallpaper: '{name}'")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # "pbc night" is shorthand for "pbc set night".
    if not argv or (argv[0] not in COMMANDS and not argv[0].startswith("-")):
        argv.insert(0, "set")

    args = build_parser().parse_args(argv)

    try:
        if args.command == "set":
            return cmd_set(args.target)
        if args.command in ("list", "ls"):
            return cmd_list()
        if args.command == "add":
            return cmd_add(args.name, args.path, args.make_default, args.aliases)
        if args.command == "random":
            return cmd_random()
        if args.command == "alias":
            return cmd_alias(args.name, args.aliases)
        if args.command == "rename":
            return cmd_rename(args.old, args.new)
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
