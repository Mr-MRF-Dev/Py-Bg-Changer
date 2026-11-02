"""Command line interface."""

from __future__ import annotations

import argparse
import difflib
import random
import sys
from pathlib import Path
from typing import NoReturn

from . import __version__, cache, config, doctor
from .errors import ConfigError, PbcError, UsageError, UserError
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


def _unknown(
    target: str, wallpapers: dict[str, str], aliases: dict[str, str]
) -> NoReturn:
    message = f"Unknown wallpaper: '{target}'"
    close = difflib.get_close_matches(target, [*wallpapers, *aliases], n=1)
    if close:
        message += f"\nDid you mean '{close[0]}'?"
    if wallpapers:
        labels = ", ".join(_label(name, aliases) for name in wallpapers)
        message += f"\nAvailable: {labels}"
    else:
        message += "\nNothing is saved yet. Save one with:  pbc add NAME IMAGE"
    raise UserError(message)


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
    except (OSError, ConfigError):
        pass  # only a convenience, never worth failing for


def cmd_set(target: str | None) -> None:
    wallpapers = config.load()
    aliases = config.load_aliases()

    if target is None:
        target = _default_name(wallpapers, aliases)
        if target is None:
            if not wallpapers:
                raise UserError(
                    "Nothing is saved yet. Save one with:  pbc add NAME IMAGE --default"
                )
            labels = ", ".join(_label(name, aliases) for name in wallpapers)
            raise UserError(
                "No default wallpaper is set. Choose one with:  pbc default NAME\n"
                f"Available: {labels}"
            )

    saved = _resolve(target, wallpapers, aliases)
    if saved is None:
        if Path(target).expanduser().is_file():
            raise UserError(
                f"'{target}' is an image file, not a saved name.\n"
                f"Save it first with:  pbc add NAME {target}"
            )
        _unknown(target, wallpapers, aliases)

    image = Path(wallpapers[saved]).expanduser()
    label = f"'{saved}'"
    if not image.is_file():
        raise UserError(
            f"File not found: {image}\nAdd it again with:  pbc add {saved} IMAGE"
        )

    set_wallpaper(image)
    _remember(image)
    print(f"Wallpaper set to {label}")


def cmd_random() -> None:
    wallpapers = config.load()
    if not wallpapers:
        raise UserError("Nothing is saved yet. Save one with:  pbc add NAME IMAGE")

    # One entry per image (two names can share one file); missing files are skipped.
    usable: dict[Path, str] = {}
    for name, path in wallpapers.items():
        image = _resolved(path)
        if image.is_file():
            usable.setdefault(image, name)
    if not usable:
        raise UserError(
            "None of the saved images exist any more. "
            "Add them again with:  pbc add NAME IMAGE"
        )

    # Avoid repeating the wallpaper that is set right now (if there is a choice).
    current = config.get_current()
    others = [
        image for image in usable if current is None or image != _resolved(current)
    ]
    cmd_set(usable[random.choice(others or list(usable))])


def _names_of(
    image: Path, wallpapers: dict[str, str], aliases: dict[str, str]
) -> list[str]:
    """The saved wallpapers (with their aliases) that use this image."""
    return [
        _label(name, aliases)
        for name, path in wallpapers.items()
        if _resolved(path) == image
    ]


def cmd_current() -> None:
    current = config.get_current()
    if current is None:
        print("Nothing has been set by py-bg-changer yet.")
        return
    image = _resolved(current)
    names = _names_of(image, config.load(), config.load_aliases())
    note = "" if image.is_file() else "  (missing)"
    print(f"{', '.join(names)}  {image}{note}" if names else f"{image}{note}")


def cmd_back() -> None:
    # Take the newest previous image that still exists.
    history = config.get_history()
    while history and not Path(history[-1]).is_file():
        history.pop()
    if not history:
        raise UserError("There is no previous wallpaper to go back to.")

    image = _resolved(history.pop())
    set_wallpaper(image)
    try:
        config.step_back(str(image), history)
    except (OSError, ConfigError):
        pass  # the wallpaper is already set, so this is not worth failing for
    names = _names_of(image, config.load(), config.load_aliases())
    print(f"Wallpaper set back to {names[0] if names else image}")


def cmd_list() -> None:
    wallpapers = config.load()
    aliases = config.load_aliases()
    if not wallpapers:
        print("Nothing saved yet. Save one with:  pbc add NAME IMAGE")
        return
    default = _default_name(wallpapers, aliases)
    labels = {name: _label(name, aliases) for name in wallpapers}
    width = max(len(label) for label in labels.values())
    for name, path in wallpapers.items():
        mark = "*" if name == default else " "
        note = "" if Path(path).expanduser().is_file() else "  (missing)"
        print(f"{mark} {labels[name]:<{width}}  {path}{note}")


def cmd_add(
    name: str, path: str, make_default: bool, alias_names: list[str] | None
) -> None:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise UserError(f"File not found: {source}")

    wallpapers = config.load()
    aliases = config.load_aliases()
    if name in aliases:
        raise UserError(
            f"'{name}' is already an alias of '{aliases[name]}'.\n"
            f"Remove the alias first with:  pbc remove {name}"
        )
    requested = _dedupe(alias_names or [])
    problem = _check_aliases(name, requested, wallpapers, aliases)
    if problem:
        raise UserError(problem)

    try:
        stored = cache.store(source)
    except OSError as exc:
        raise UserError(f"Could not copy {source}: {exc}") from exc

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


def cmd_alias(name: str, new_aliases: list[str]) -> None:
    wallpapers = config.load()
    aliases = config.load_aliases()
    real = _resolve(name, wallpapers, aliases)
    if real is None:
        _unknown(name, wallpapers, aliases)

    requested = _dedupe(new_aliases)
    problem = _check_aliases(real, requested, wallpapers, aliases)
    if problem:
        raise UserError(problem)

    added = [alias for alias in requested if alias not in aliases]
    if not added:
        print(f"'{real}' already has those aliases")
        return
    for alias in added:
        aliases[alias] = real
    config.save(wallpapers, aliases)
    print(f"'{real}' is now also called: {', '.join(added)}")


def cmd_rename(old: str, new: str) -> None:
    wallpapers = config.load()
    aliases = config.load_aliases()
    if old not in wallpapers and old not in aliases:
        _unknown(old, wallpapers, aliases)
    if new == old:
        print(f"'{old}' is already called that")
        return
    if new in wallpapers:
        raise UserError(f"'{new}' is already a saved wallpaper name.")
    if new in aliases:
        raise UserError(f"'{new}' is already an alias of '{aliases[new]}'.")

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


def cmd_default(name: str | None) -> None:
    wallpapers = config.load()
    aliases = config.load_aliases()
    if name is None:
        current = config.get_default()
        resolved = _resolve(current, wallpapers, aliases) if current else None
        if resolved:
            print(resolved)
        else:
            print("No default set. Choose one with:  pbc default NAME")
        return
    resolved = _resolve(name, wallpapers, aliases)
    if resolved is None:
        _unknown(name, wallpapers, aliases)
    config.set_default(resolved)
    print(f"'{resolved}' is now the default wallpaper")


def cmd_remove(name: str) -> None:
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
        return

    if name in aliases:
        target = aliases.pop(name)
        config.save(wallpapers, aliases)
        print(f"Removed alias '{name}' (the wallpaper '{target}' is still saved)")
        return

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
