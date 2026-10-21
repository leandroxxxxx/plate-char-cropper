"""Output filename construction and sanitization.

Pure logic with no GUI dependencies. Builds crop filenames according to the
convention::

    {source_stem}_{character}.png

For example, source ``0001_video_00-01-23.450.png`` and character ``A``
produce ``0001_video_00-01-23.450_A.png``.

When two crops of one plate would get the same name (a repeated character),
the caller adds the 1-based position before the character::

    {source_stem}_{position}_{character}.png
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
    stem: str, character: str, position: int | None = None
) -> str:
    """Build one output filename.

    Without ``position``: ``{stem}_{character}.png``. With it (used when plain
    names would collide): ``{stem}_{position}_{character}.png``. The character
    label is always the last part of the name.
    """
    label = sanitize_character_label(character)
    if position is None:
        return f"{stem}_{label}.png"
    return f"{stem}_{position}_{label}.png"


def destination_path(
    folder: Path | str,
    source_path: Path | str,
    character: str,
    position: int | None = None,
) -> Path:
    """Full destination path for one character crop inside ``folder``."""
    name = build_filename(source_stem(source_path), character, position)
    return Path(folder) / name
