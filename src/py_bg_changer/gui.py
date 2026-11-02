"""Entry point without a console window, for Win+R and other launchers.

It runs the same commands as `pbc`, but stays silent when everything works and
shows a small message box when something goes wrong (there is no console to
print errors to).
"""

from __future__ import annotations

import contextlib
import io
import sys

from .cli import run as cli_run
from .errors import PbcError

TITLE = "py-bg-changer"


def _show_error(message: str) -> None:
    if sys.platform == "win32":
        import ctypes

        MB_ICONERROR = 0x10
        MB_TOPMOST = 0x40000
        ctypes.windll.user32.MessageBoxW(
            None, message, TITLE, MB_ICONERROR | MB_TOPMOST
        )
    else:
        print(message, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    out = io.StringIO()
    message = ""
    code = 0
    with contextlib.redirect_stdout(out):
        try:
            code = cli_run(argv)
        except PbcError as exc:
            message, code = str(exc), exc.exit_code
        except SystemExit as exc:  # argparse exits for --help and --version
            code = exc.code if isinstance(exc.code, int) else int(exc.code is not None)
        except Exception as exc:  # never let a traceback vanish into a missing console
            message, code = f"Unexpected error: {exc}", 1
    if code != 0:
        # Commands like `doctor` print their report and return 1: show that report.
        _show_error(
            message
            or out.getvalue().strip()
            or f"Something went wrong (exit code {code})."
        )
    return code
