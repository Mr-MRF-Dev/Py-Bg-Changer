"""Our own copy of every saved wallpaper.

When an image is added we copy it next to the config file and hand that copy to
the operating system, so the wallpaper keeps working even if the original file
is moved or deleted.

Copies are named after a hash of their content: adding the same image under two
names stores it once, and the copy is deleted when no saved name uses it.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from . import config


def cache_dir() -> Path:
    return config.config_path().expanduser().resolve().parent / "wallpapers"


def store(source: Path) -> Path:
    """Copy `source` into the cache (if it isn't there yet) and return the copy."""
    digest = hashlib.sha256()
    with source.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    dest = cache_dir() / f"{digest.hexdigest()[:16]}{source.suffix.lower()}"
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".tmp")
        shutil.copyfile(source, tmp)
        tmp.replace(dest)
    return dest


def release(path: str, wallpapers: dict[str, str]) -> None:
    """Delete a cached copy once no saved name points to it any more."""
    if path in wallpapers.values():
        return
    try:
        target = Path(path).expanduser().resolve()
        if target.parent == cache_dir():
            target.unlink()
    except OSError:
        pass
