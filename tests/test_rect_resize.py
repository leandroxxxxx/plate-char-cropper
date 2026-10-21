"""Tests for the aspect-ratio-locked resize math (no window needed)."""

import pytest
from PySide6.QtCore import QRectF

from platechar_annotator.ui.rect_item import _Edge, _resized_rect_locked

RATIO = 2.0  # width / height
BOUNDS = QRectF(0, 0, 100, 100)
START = QRectF(10, 10, 40, 20)  # Already 2:1.


def as_tuple(rect: QRectF) -> tuple[float, float, float, float]:
    return (rect.x(), rect.y(), rect.width(), rect.height())


def test_right_edge_scales_height_and_stays_centred():
    rect = _resized_rect_locked(START, _Edge.RIGHT, 20, 0, BOUNDS, RATIO)
    assert as_tuple(rect) == pytest.approx((10, 5, 60, 30))


def test_bottom_right_corner_keeps_top_left_fixed():
    rect = _resized_rect_locked(START, _Edge.RIGHT | _Edge.BOTTOM, 10, 0, BOUNDS, RATIO)
    assert as_tuple(rect) == pytest.approx((10, 10, 50, 25))


def test_top_left_corner_keeps_bottom_right_fixed():
    rect = _resized_rect_locked(START, _Edge.LEFT | _Edge.TOP, -10, 0, BOUNDS, RATIO)
    assert as_tuple(rect) == pytest.approx((0, 5, 50, 25))
    assert rect.right() == pytest.approx(START.right())
    assert rect.bottom() == pytest.approx(START.bottom())


def test_growth_is_limited_by_the_image_bounds():
    rect = _resized_rect_locked(START, _Edge.RIGHT, 500, 0, BOUNDS, RATIO)
    assert as_tuple(rect) == pytest.approx((10, 0, 80, 40))


def test_shrinking_stops_at_the_minimum_size():
    rect = _resized_rect_locked(START, _Edge.RIGHT, -100, 0, BOUNDS, RATIO)
    assert as_tuple(rect) == pytest.approx((10, 19, 4, 2))


def test_rectangle_is_unchanged_when_no_size_fits_ratio_and_bounds():
    tiny = QRectF(0, 0, 3, 3)
    rect = _resized_rect_locked(tiny, _Edge.RIGHT, 1, 0, tiny, RATIO)
    assert as_tuple(rect) == (0, 0, 3, 3)


ALL_EDGES = [
    _Edge.LEFT,
    _Edge.RIGHT,
    _Edge.TOP,
    _Edge.BOTTOM,
    _Edge.LEFT | _Edge.TOP,
    _Edge.RIGHT | _Edge.TOP,
    _Edge.LEFT | _Edge.BOTTOM,
    _Edge.RIGHT | _Edge.BOTTOM,
]


@pytest.mark.parametrize("edges", ALL_EDGES)
@pytest.mark.parametrize(
    "delta",
    [(-30, -30), (15, -5), (40, 40), (-100, 100), (500, 500), (-500, -500)],
)
def test_ratio_holds_and_rectangle_stays_valid(edges, delta):
    rect = _resized_rect_locked(START, edges, delta[0], delta[1], BOUNDS, RATIO)
    assert rect.width() / rect.height() == pytest.approx(RATIO)
    assert rect.left() >= -1e-9
    assert rect.top() >= -1e-9
    assert rect.right() <= 100 + 1e-9
    assert rect.bottom() <= 100 + 1e-9
    assert rect.width() >= 2 - 1e-9
    assert rect.height() >= 2 - 1e-9