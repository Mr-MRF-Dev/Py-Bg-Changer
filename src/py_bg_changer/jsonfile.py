"""Reading and writing the JSON files of the program."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .errors import ConfigError


def read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # ValueError: bad JSON or bad UTF-8
        raise ConfigError(f"Could not read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path} has an unexpected format (expected a JSON object).")
    return data


def write(path: Path, data: dict[str, Any]) -> None:
    """Replace the file in one step: it is the old content or the new one, never half.

    The new content is written to a file of its own first (so two programs writing at
    the same time do not mix), and a link to the file is followed, not replaced.
    """
    if path.is_symlink():
        path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f"{path.name}.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            shutil.copymode(path, tmp)  # a file that was readable by others stays so
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
