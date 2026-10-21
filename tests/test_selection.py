"""Tests for the rectangle row layout (no GUI needed)."""

import pytest

from platechar_annotator.models.selection import (
    CHARACTER_COUNT,
    DEFAULT_SIZE_FRACTION,
    MAX_SIZE_FRACTION,
    create_default_rectangles,
    create_rectangles_in_region,
)

REGION = (100.0, 50.0, 700.0, 300.0)  # x, y, width, height


def test_row_is_seven_equal_touching_rectangles_numbered_left_to_right():
    rects = create_rectangles_in_region(*REGION)
    assert [rect.index for rect in rects] == list(range(1, CHARACTER_COUNT + 1))
    for rect in rects:
        assert rect.width == pytest.approx(rects[0].width)
        assert rect.height == pytest.approx(rects[0].height)
        assert rect.y == pytest.approx(rects[0].y)
    for left, right in zip(rects, rects[1:]):
        assert right.x == pytest.approx(left.x + left.width)


@pytest.mark.parametrize("ratio", [0.25, 0.5, 1.0, 2.0, 4.5])
def test_every_rectangle_has_the_requested_aspect_ratio(ratio):
    for rect in create_rectangles_in_region(*REGION, aspect_ratio=ratio):
        assert rect.width / rect.height == pytest.approx(ratio)


@pytest.mark.parametrize("ratio", [None, 0.25, 0.5, 1.0, 2.0, 4.5])
def test_row_stays_inside_the_region_and_is_centred(ratio):
    x, y, width, height = REGION
    rects = create_rectangles_in_region(*REGION, aspect_ratio=ratio)
    row_left = rects[0].x
    row_right = rects[-1].x + rects[-1].width
    assert row_left >= x - 1e-9
    assert row_right <= x + width + 1e-9
    assert (row_left + row_right) / 2 == pytest.approx(x + width / 2)
    for rect in rects:
        assert rect.y >= y - 1e-9
        assert rect.y + rect.height <= y + height + 1e-9
        assert rect.y + rect.height / 2 == pytest.approx(y + height / 2)


def test_full_size_without_ratio_fills_the_region():
    x, y, width, height = REGION
    rects = create_rectangles_in_region(*REGION, size_fraction=MAX_SIZE_FRACTION)
    assert rects[0].x == pytest.approx(x)
    assert rects[-1].x + rects[-1].width == pytest.approx(x + width)
    assert rects[0].y == pytest.approx(y)
    assert rects[0].height == pytest.approx(height)


def test_size_fraction_scales_the_whole_row():
    full = create_rectangles_in_region(*REGION, aspect_ratio=0.5, size_fraction=1.0)
    half = create_rectangles_in_region(*REGION, aspect_ratio=0.5, size_fraction=0.5)
    assert half[0].width == pytest.approx(full[0].width / 2)
    assert half[0].height == pytest.approx(full[0].height / 2)
    for left, right in zip(half, half[1:]):
        assert right.x == pytest.approx(left.x + left.width)


def test_height_limit_applies_when_the_row_would_be_too_tall():
    rects = create_rectangles_in_region(
        0, 0, 1000, 100, aspect_ratio=1.0, size_fraction=1.0
    )
    assert rects[0].height == pytest.approx(100)
    assert rects[0].width == pytest.approx(100)
    assert rects[0].x == pytest.approx(150)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"aspect_ratio": 0},
        {"aspect_ratio": -1.0},
        {"aspect_ratio": float("nan")},
        {"aspect_ratio": float("inf")},
        {"size_fraction": 0},
        {"size_fraction": -0.2},
        {"size_fraction": 1.5},
    ],
)
def test_invalid_arguments_raise(kwargs):
    with pytest.raises(ValueError):
        create_rectangles_in_region(*REGION, **kwargs)


@pytest.mark.parametrize("region", [(0, 0, 0, 10), (0, 0, 10, 0), (0, 0, -5, 10)])
def test_empty_regions_raise(region):
    with pytest.raises(ValueError):
        create_rectangles_in_region(*region)


def test_default_rectangles_use_the_default_size_over_the_whole_image():
    rects = create_default_rectangles(200, 100)
    assert len(rects) == CHARACTER_COUNT
    assert rects[0].height == pytest.approx(100 * DEFAULT_SIZE_FRACTION)
    assert rects[0].x == pytest.approx(30)  # (200 - 7 * 20) / 2


def test_default_rectangles_reject_invalid_dimensions():
    with pytest.raises(ValueError):
        create_default_rectangles(0, 100)