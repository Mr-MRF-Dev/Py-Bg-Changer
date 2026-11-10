"""Moving the saved files to a newer layout (see `schema.py` for the versions).

It runs before every command (`cli.run`), so a command never sees old files. The rules
that keep a user's data safe:

1. Nothing is changed before a backup of `config.json` exists. The first backup is
   kept: it is the original, and a second attempt never replaces it.
2. Every file is replaced in one step (`jsonfile.write`), so it is the old file or the
   new one, never half of it.
3. The new files are written first and the old keys are removed last. If the program
   stops in between, everything is still readable and the next run finishes the job.
4. It looks at the files, not at a record of what was done, so running it again (after a
   crash, or when two programs start together) does nothing more than what is missing.
5. A lock file keeps two programs from migrating at the same time. Whoever gets the lock
   looks again, because the other one may have finished while it waited.
6. A file from a newer py-bg-changer is never touched.
7. Files that need nothing are not written at all (a config that is read-only is fine).

To add a layout: raise `schema.CURRENT_VERSION`, write a function that moves files from
the previous layout and register it in `STEPS`.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from . import config, jsonfile, schema
from .errors import ConfigError
from .state import HISTORY_LIMIT

LOCK_TIMEOUT = 5.0  # seconds to wait for another program that is migrating
LOCK_STALE = 30.0  # a lock that is older than this was left behind by a crash


@dataclass(frozen=True)
class Migration:
    """What was done, to tell the user once."""

    from_version: int
    to_version: int
    backup: Path
    config_file: Path
    state_file: Path

    @property
    def notice(self) -> str:
        return (
            f"py-bg-changer: your saved files were moved to a new layout "
            f"({self.from_version} -> {self.to_version}).\n"
            f"  The wallpaper that is set now and the history are in {self.state_file}.\n"
            f"  A backup of your old config is at {self.backup}."
        )


def migrate() -> Migration | None:
    """Bring the saved files to the current layout. None if they already were."""
    path = config.config_path()
    if not path.exists():
        return None  # nothing saved yet
    version = _layout(path)
    if version == schema.CURRENT_VERSION:
        return None

    try:
        with _lock(path):
            version = _layout(path)  # the program that had the lock may have finished
            if version == schema.CURRENT_VERSION:
                return None
            backup = _backup(path, version)
            for step in range(version, schema.CURRENT_VERSION):
                STEPS[step]()
    except OSError as exc:
        raise ConfigError(
            f"Could not move your saved files to the new layout: {exc}\n"
            "Your config was not damaged (a backup is next to it once one was made). "
            "Fix the problem and run the command again."
        ) from exc
    return Migration(version, schema.CURRENT_VERSION, backup, path, config.state_path())


def _layout(path: Path) -> int:
    data = jsonfile.read(path)
    version = schema.config_version(data, path)
    schema.check_supported(version, path)
    return version


def _backup(path: Path, version: int) -> Path:
    backup = path.with_name(f"{path.name}.v{version}.bak")
    if backup.exists():
        return backup  # from an earlier attempt: that one is the original
    tmp = backup.with_name(backup.name + f".{os.getpid()}.tmp")
    try:
        shutil.copy2(path, tmp)
        tmp.replace(backup)  # a backup that exists is a complete one
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return backup


@contextlib.contextmanager
def _lock(path: Path) -> Iterator[None]:
    lock = path.with_name(path.name + ".lock")
    deadline = time.monotonic() + LOCK_TIMEOUT
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > LOCK_STALE:
                    lock.unlink()
                    continue
            except FileNotFoundError:
                continue  # it was just released: try again
            if time.monotonic() > deadline:
                raise ConfigError(
                    f"Another py-bg-changer is moving your files (waited {LOCK_TIMEOUT:g}s). "
                    f"If none is running, delete {lock} and try again."
                ) from None
            time.sleep(0.02)
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


# --- 1 -> 2: current and history move from config.json to state.json ----------------


def _v1_to_v2() -> None:
    config_file = config.config_path()
    state_file = config.state_path()
    data = jsonfile.read(config_file)

    if state_file.exists():
        # Already there (an earlier attempt got this far): it is newer than the old
        # keys, so it stays. It has to be readable, or the old keys would be lost.
        schema.check_supported(
            schema.declared_version(jsonfile.read(state_file), state_file) or 1,
            state_file,
        )
    else:
        current = data.get("current")
        current = current if isinstance(current, str) and current else None
        history = data.get("history")
        history = (
            [i for i in history if isinstance(i, str)]
            if isinstance(history, list)
            else []
        )
        # An earlier format also kept the image that is set now at the end of the
        # history. It does not belong there.
        while history and history[-1] == data.get("current"):
            history.pop()
        state = {"version": schema.CURRENT_VERSION, "history": history[-HISTORY_LIMIT:]}
        if current:
            state["current"] = current
        jsonfile.write(state_file, state)

    for key in schema.STATE_KEYS:
        data.pop(key, None)
    data["version"] = schema.CURRENT_VERSION
    jsonfile.write(
        config_file, data
    )  # last: this is the step that removes the old keys


# What moves files from one layout to the next, by the layout it starts from.
STEPS: dict[int, Callable[[], None]] = {1: _v1_to_v2}
