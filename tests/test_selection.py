"""Tests for rectangle layout inside a region (no GUI needed)."""

import pytest

from platechar_annotator.models.selection import (
    CHARACTER_COUNT,
    create_default_rectangles,
    create_rectangles_in_region,
)


def test_seven_rectangles_numbered_left_to_right():
    rects = create_rectangles_in_region(0, 0, 700, 100)
    assert [rect.index for rect in rects] == list(range(1, 8))
    xs = [rect.x for rect in rects]
    assert xs == sorted(xs)


def test_rectangles_lie_fully_inside_region():
    region = (50.0, 30.0, 600.0, 80.0)
    x, y, width, height = region
    for rect in create_rectangles_in_region(x, y, width, height):
        assert rect.x >= x
        assert rect.y >= y
        assert rect.width > 0
        assert rect.height > 0
        assert rect.x + rect.width <= x + width
        assert rect.y + rect.height <= y + height


def test_fractional_visible_region_still_contains_all_rectangles():
    # Simulates a zoomed view: fractional origin, odd size.
    region = (123.7, 45.2, 311.4, 57.9)
    x, y, width, height = region
    rects = create_rectangles_in_region(x, y, width, height)
    assert len(rects) == CHARACTER_COUNT
    for rect in rects:
        assert rect.x >= x
        assert rect.x + rect.width <= x + width + 1e-9


def test_default_layout_matches_whole_image_region():
    whole = create_rectangles_in_region(0, 0, 700, 100)
    default = create_default_rectangles(700, 100)
    assert whole == default


@pytest.mark.parametrize(
    "region",
    [
        (0, 0, 0, 100),
        (0, 0, 700, 0),
        (0, 0, -10, 100),
        (0, 0, 100, -5),
    ],
)
def test_non_positive_region_raises(region):
    with pytest.raises(ValueError):
        create_rectangles_in_region(*region)
