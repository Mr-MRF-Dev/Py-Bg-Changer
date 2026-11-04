"""Command line interface.

The commands themselves live in `commands/`. This module only builds the parser from
their list, runs the right one and shows the problems they raise.
"""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

from . import __version__
from .commands import COMMANDS, all_names
from .errors import PbcError, UsageError

DEFAULT_COMMAND = "set"  # `pbc night` means `pbc set night`


class _Parser(argparse.ArgumentParser):
    """argparse, but a wrong command line is an error to raise, not a reason to exit."""

    def error(self, message: str) -> NoReturn:
        raise UsageError(f"{self.format_usage()}{self.prog}: error: {message}")


def _epilog() -> str:
    examples = [example for command in COMMANDS for example in command.examples]
    width = max(37, max(len(text) for text, _ in examples) + 2)
    lines = [f"  {text:<{width}}{what}" for text, what in examples]
    return "'pbc' is a short alias for 'py-bg-changer'.\n\nexamples:\n" + "\n".join(
        lines
    )


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="py-bg-changer",
        description="Change your desktop wallpaper from the command line.",
        epilog=_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    for command in COMMANDS:
        p = sub.add_parser(
            command.name, aliases=list(command.aliases), help=command.help
        )
        # Remember which function runs it and which of its arguments it takes.
        dests = [p.add_argument(*a.flags, **a.options).dest for a in command.args]
        p.set_defaults(_handler=command.handler, _dests=dests)
    return parser


def run(argv: list[str] | None = None) -> int:
    """Run one command and return its exit code.

    Problems are raised as `PbcError`; `main` shows them in the terminal.
    """
    args_list = list(sys.argv[1:] if argv is None else argv)

    # "pbc night" is shorthand for "pbc set night".
    if not args_list or (
        args_list[0] not in all_names() and not args_list[0].startswith("-")
    ):
        args_list.insert(0, DEFAULT_COMMAND)

    args = build_parser().parse_args(args_list)
    handler = getattr(args, "_handler", None)
    if handler is None:
        return 0
    result: int | None = handler(**{dest: getattr(args, dest) for dest in args._dests})
    return result or 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except PbcError as exc:
        print(exc, file=sys.stderr)
        return exc.exit_code
