"""The list of commands.

Every command is described once, right above the function that runs it: its name, its
arguments, its help text and its examples. The command line parser, the shorthand
(`pbc night` means `pbc set night`) and the examples in `--help` are all built from
this list, so adding a command means writing one function with `@command(...)`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

Handler = TypeVar("Handler", bound=Callable[..., int | None])


@dataclass(frozen=True)
class Arg:
    flags: tuple[str, ...]
    options: dict[str, Any]


def arg(*flags: str, **options: Any) -> Arg:
    """An argument of a command. It takes the same parameters as argparse."""
    return Arg(flags, options)


@dataclass(frozen=True)
class Command:
    name: str
    help: str
    handler: Callable[..., int | None]
    aliases: tuple[str, ...] = ()
    args: tuple[Arg, ...] = ()
    examples: tuple[tuple[str, str], ...] = ()  # (what to type, what it does)
    migrate: bool = True  # move old saved files to the new layout before running it


COMMANDS: list[Command] = []


def all_names() -> set[str]:
    """The names of all commands, including their short aliases."""
    return {name for cmd in COMMANDS for name in (cmd.name, *cmd.aliases)}


def command(
    name: str,
    *,
    help: str,
    aliases: tuple[str, ...] = (),
    args: tuple[Arg, ...] = (),
    examples: tuple[tuple[str, str], ...] = (),
    migrate: bool = True,
) -> Callable[[Handler], Handler]:
    """Register the function below as a command.

    The function gets one parameter for each argument, named like the argument's
    `dest` (the name of the argument, or `dest=` when it is given). It returns None,
    or an exit code when it needs one other than 0. Problems are raised as `PbcError`.

    Old saved files are migrated before it runs, unless `migrate=False`: a command that
    has to work even when the files are broken (`doctor`, `path`) must not fail early.
    """

    def register(handler: Handler) -> Handler:
        taken = all_names() & {name, *aliases}
        if taken:
            raise ValueError(f"command name already in use: {', '.join(sorted(taken))}")
        COMMANDS.append(Command(name, help, handler, aliases, args, examples, migrate))
        return handler

    return register
