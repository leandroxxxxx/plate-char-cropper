"""Tests for coordinate conversion and crop extraction (no GUI needed)."""

import pytest
from PIL import Image

from platechar_annotator.models.selection import (
    CharacterRect,
    create_default_rectangles,
)
from platechar_annotator.services.crop_service import (
    CropError,
    PixelBox,
    crop_character,
    rect_to_pixel_box,
)


def make_rect(
    x: float, y: float, width: float, height: float, index: int = 1
) -> CharacterRect:
    return CharacterRect(index=index, x=x, y=y, width=width, height=height)


def make_gradient_image(width: int, height: int) -> Image.Image:
    """RGB image where pixel (x, y) is (x, y, 0), so crops are easy to verify."""
    image = Image.new("RGB", (width, height))
    image.putdata([(x, y, 0) for y in range(height) for x in range(width)])
    return image


def test_integer_rectangle_maps_exactly():
    box = rect_to_pixel_box(make_rect(10, 20, 30, 40), 100, 100)
    assert box == PixelBox(10, 20, 40, 60)
    assert (box.width, box.height) == (30, 40)


def test_fractional_edges_round_to_nearest_pixel_halves_up():
    # left 10.4 -> 10, top 20.5 -> 21 (half up), right 40.6 -> 41, bottom 60.49 -> 60
    box = rect_to_pixel_box(make_rect(10.4, 20.5, 30.2, 39.99), 100, 100)
    assert box == PixelBox(10, 21, 41, 60)


@pytest.mark.parametrize(
    ("rect", "expected"),
    [
        (make_rect(-5, -5, 20, 20), PixelBox(0, 0, 15, 15)),
        (make_rect(90, 90, 30, 30), PixelBox(90, 90, 100, 100)),
        (make_rect(-10, -10, 500, 500), PixelBox(0, 0, 100, 100)),
    ],
    ids=["top-left", "bottom-right", "covers-everything"],
)
def test_rectangle_is_clamped_to_image_bounds(rect, expected):
    assert rect_to_pixel_box(rect, 100, 100) == expected


@pytest.mark.parametrize(
    "rect",
    [
        make_rect(150, 10, 20, 20),
        make_rect(10, 150, 20, 20),
        make_rect(10, 10, 0, 20),
        make_rect(10, 10, 20, 0),
        make_rect(10, 10, -5, 5),
    ],
    ids=["right-of-image", "below-image", "zero-width", "zero-height", "inverted"],
)
def test_rectangle_without_pixels_in_image_raises(rect):
    with pytest.raises(CropError):
        rect_to_pixel_box(rect, 100, 100)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf")])
def test_non_finite_coordinates_raise(bad_value):
    with pytest.raises(CropError):
        rect_to_pixel_box(make_rect(bad_value, 0, 10, 10), 100, 100)


def test_crop_has_expected_dimensions():
    image = Image.new("RGB", (200, 100))
    crop = crop_character(image, make_rect(10, 20, 30, 40))
    assert crop.size == (30, 40)


def test_crop_pixels_come_from_the_right_region():
    image = make_gradient_image(200, 100)
    crop = crop_character(image, make_rect(10, 20, 5, 4))
    assert crop.size == (5, 4)
    assert crop.getpixel((0, 0)) == (10, 20, 0)
    assert crop.getpixel((4, 3)) == (14, 23, 0)


def test_crop_keeps_mode_and_leaves_source_untouched():
    image = Image.new("L", (50, 50), 7)
    crop = crop_character(image, make_rect(5, 5, 10, 10))
    assert crop.mode == "L"
    assert crop.getpixel((0, 0)) == 7
    assert image.size == (50, 50)
    assert image.getpixel((0, 0)) == 7


@pytest.mark.parametrize("size", [(200, 100), (94, 24), (1000, 300)])
def test_default_rectangles_all_produce_valid_crops(size):
    width, height = size
    image = Image.new("RGB", size)
    rects = create_default_rectangles(width, height)
    assert [rect.index for rect in rects] == list(range(1, 8))
    for rect in rects:
        crop = crop_character(image, rect)
        assert crop.width > 0
        assert crop.height > 0