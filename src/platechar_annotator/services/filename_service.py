"""Output filename construction and sanitization.

Pure logic with no GUI dependencies. Builds crop filenames according to the
convention::

    {timestamp}_{source_stem}_{character}.png

One timestamp is shared by a save batch. A position is added only when labels
repeat within the batch, to keep those filenames distinct.
"""

from pathlib import Path

# Characters forbidden in Windows filenames, plus ASCII control characters.
# Linux itself only forbids NUL and ``/``; using the Windows set keeps the
# application portable without over-sanitizing ordinary plate characters.
_INVALID_FILENAME_CHARS = frozenset('<>:"/\\|?*') | {chr(code) for code in range(32)}

_REPLACEMENT = "_"


def source_stem(path: Path | str) -> str:
    """Return the source filename without its final extension.

    Only the last suffix is removed, so dots inside the name are preserved:

    ``0001_video_00-01-23.450.png`` -> ``0001_video_00-01-23.450``
    """
    return Path(path).stem


def sanitize_character_label(character: str) -> str:
    """Return ``character`` made safe to embed in a filename.

    Characters invalid on supported operating systems are replaced with
    ``_``. Standard alphanumeric license-plate characters pass through
    unchanged. A label with no usable characters becomes ``_``.
    """
    if not character:
        return _REPLACEMENT

    sanitized = "".join(
        _REPLACEMENT if ch in _INVALID_FILENAME_CHARS else ch
        for ch in character
    )

    if not sanitized or set(sanitized) <= {_REPLACEMENT}:
        return _REPLACEMENT
    return sanitized


def build_filename(
    stem: str, character: str, timestamp: str, position: int | None = None
) -> str:
    """Build a time-ordered filename, optionally disambiguated by position."""
    label = sanitize_character_label(character)
    suffix = f"_{position}" if position is not None else ""
    return f"{timestamp}_{stem}{suffix}_{label}.png"


def destination_path(
    folder: Path | str,
    source_path: Path | str,
    character: str,
    timestamp: str,
    position: int | None = None,
) -> Path:
    """Full destination path for one character crop inside ``folder``."""
    name = build_filename(source_stem(source_path), character, timestamp, position)
    return Path(folder) / name
