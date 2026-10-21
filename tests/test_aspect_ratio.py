"""Tests for aspect-ratio parsing (no GUI needed)."""

import pytest

from platechar_annotator.services.aspect_ratio import parse_aspect_ratio


@pytest.mark.parametrize(
    ("width", "height", "expected"),
    [
        ("1", "2", 0.5),
        ("3", "1", 3.0),
        ("1", "1", 1.0),
        ("2.5", "5", 0.5),
        ("2,5", "5", 0.5),
        (" 4 ", " 2 ", 2.0),
    ],
)
def test_valid_fields_give_width_over_height(width, height, expected):
    assert parse_aspect_ratio(width, height) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("width", "height"),
    [
        ("", "2"),
        ("1", ""),
        ("", ""),
        ("0", "2"),
        ("1", "0"),
        (".", "2"),
        ("abc", "2"),
        ("-1", "2"),
        ("9" * 400, "1"),
    ],
)
def test_empty_or_invalid_fields_mean_free_resizing(width, height):
    assert parse_aspect_ratio(width, height) is None