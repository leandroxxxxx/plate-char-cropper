"""Parsing of the aspect-ratio fields.

No GUI dependencies.
"""

import math


def _parse_positive_number(text: str) -> float | None:
    """Parse a positive finite number ('.' or ',' decimals); None if invalid."""
    try:
        value = float(text.strip().replace(",", "."))
    except ValueError:
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return value


def parse_aspect_ratio(width_text: str, height_text: str) -> float | None:
    """Return width / height from two text fields, or None for free resizing.

    Both fields must hold a positive number. If either is empty or invalid,
    the ratio is not locked and None is returned.
    """
    width = _parse_positive_number(width_text)
    height = _parse_positive_number(height_text)
    if width is None or height is None:
        return None
    ratio = width / height
    return ratio if math.isfinite(ratio) and ratio > 0 else None