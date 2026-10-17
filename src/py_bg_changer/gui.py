"""Entry point without a console window, for Win+R and other launchers.

It runs the same commands as `pbc`, but stays silent when everything works and
shows a small message box when something goes wrong (there is no console to
print errors to).
"""

from __future__ import annotations

import contextlib
import io
import sys

from .cli import main as cli_main

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
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli_main(argv)
        except SystemExit as exc:  # argparse exits on bad arguments, --help, --version
            code = exc.code if isinstance(exc.code, int) else int(exc.code is not None)
        except Exception as exc:  # never let a traceback vanish into a missing console
            code = 1
            err.write(f"Unexpected error: {exc}")
    if code != 0:
        message = err.getvalue().strip() or out.getvalue().strip()
        _show_error(message or f"Something went wrong (exit code {code}).")
    return code
