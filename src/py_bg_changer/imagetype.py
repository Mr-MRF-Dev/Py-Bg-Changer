"""Is this file an image that can be a wallpaper?

`pbc add` only saves a file when both of these say yes:

1. its extension is one of `EXTENSIONS`, and
2. its first bytes are the signature (the "magic number") of a known image format.

The second check is what stops a text file that was renamed to `.png`. The two are not
compared with each other: a PNG that is called `.jpg` is still a real image.

Nothing in here touches the desktop or the saved files.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .errors import UserError

EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".webp",
    ".tif",
    ".tiff",
    ".heic",
    ".heif",
)

HEADER_SIZE = 32  # bytes of the file that are enough to tell every format apart

_BMP_HEADER_SIZES = (
    12,
    16,
    40,
    52,
    56,
    64,
    108,
    124,
)  # the DIB header that follows "BM"
_HEIF_BRANDS = (b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1")


def _is_bmp(header: bytes) -> bool:
    # "BM" alone is too short a signature (plain text can start with it), so the size
    # of the header that comes after it has to make sense too.
    return (
        header.startswith(b"BM")
        and len(header) >= 18
        and int.from_bytes(header[14:18], "little") in _BMP_HEADER_SIZES
    )


# format name -> does this start of a file look like it?
FORMATS: dict[str, Callable[[bytes], bool]] = {
    "png": lambda h: h.startswith(b"\x89PNG\r\n\x1a\n"),
    "jpeg": lambda h: h.startswith(b"\xff\xd8\xff"),
    "gif": lambda h: h.startswith((b"GIF87a", b"GIF89a")),
    "bmp": _is_bmp,
    "webp": lambda h: h[:4] == b"RIFF" and h[8:12] == b"WEBP",
    "tiff": lambda h: h.startswith((b"II*\x00", b"MM\x00*")),
    "heif": lambda h: h[4:8] == b"ftyp" and h[8:12] in _HEIF_BRANDS,
}


def supported() -> str:
    """The accepted extensions for a message, e.g. "png, jpg, jpeg, ..."."""
    return ", ".join(extension.lstrip(".") for extension in EXTENSIONS)


def detect(header: bytes) -> str | None:
    """The format that these first bytes belong to, or None if it is not an image."""
    for name, looks_like in FORMATS.items():
        if looks_like(header):
            return name
    return None


def check(path: Path) -> None:
    """Raise `UserError` unless this file is an image of a supported type."""
    suffix = path.suffix.lower()
    if suffix not in EXTENSIONS:
        shown = suffix if suffix else "no extension"
        raise UserError(
            f"'{path.name}' is not a supported image type ({shown}).\n"
            f"Supported: {supported()}"
        )
    try:
        with path.open("rb") as f:
            header = f.read(HEADER_SIZE)
    except OSError as exc:
        raise UserError(f"Could not read {path}: {exc}") from exc
    if detect(header) is None:
        raise UserError(
            f"'{path.name}' is not a real image: its content does not match any "
            "supported format.\n"
            "Is the file damaged, or was it renamed from another type?"
        )
