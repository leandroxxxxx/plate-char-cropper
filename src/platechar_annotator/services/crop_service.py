"""Coordinate conversion and crop extraction.

Rectangles are stored in original-image pixel coordinates (as floats), so no
display-scale conversion is needed here: the GUI scene is 1:1 with the
original image and Qt handles the on-screen scaling. This module turns a
rectangle into an integer pixel box and cuts it from the original image.

No GUI dependencies.
"""

import math
from dataclasses import dataclass

from PIL import Image

from platechar_annotator.models.selection import CharacterRect


class CropError(Exception):
    """Raised when a rectangle does not define a valid crop region."""


@dataclass(frozen=True)
class PixelBox:
    """An integer pixel region of an image.

    ``left``/``top`` are inclusive and ``right``/``bottom`` are exclusive,
    matching ``PIL.Image.crop``.
    """

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.left, self.top, self.right, self.bottom)


def _round_half_up(value: float) -> int:
    """Round to the nearest integer, with halves rounding up (not to even)."""
    return math.floor(value + 0.5)


def rect_to_pixel_box(
    rect: CharacterRect, image_width: int, image_height: int
) -> PixelBox:
    """Convert a rectangle (original-image pixels) to an integer pixel box.

    Each edge is rounded to the nearest pixel and the box is clamped to the
    image bounds.

    Raises:
        CropError: if the coordinates are not finite, or the rectangle covers
            no pixels of the image.
    """
    values = (rect.x, rect.y, rect.width, rect.height)
    if not all(math.isfinite(value) for value in values):
        raise CropError(f"Rectangle {rect.index} has invalid coordinates.")

    left = max(0, _round_half_up(rect.x))
    top = max(0, _round_half_up(rect.y))
    right = min(image_width, _round_half_up(rect.x + rect.width))
    bottom = min(image_height, _round_half_up(rect.y + rect.height))

    if right <= left or bottom <= top:
        raise CropError(f"Rectangle {rect.index} covers no pixels of the image.")
    return PixelBox(left, top, right, bottom)


def crop_character(image: Image.Image, rect: CharacterRect) -> Image.Image:
    """Cut the rectangle's pixels out of the original image.

    The crop keeps the source mode and pixel values: no resizing, filtering,
    or other processing is applied.

    Raises:
        CropError: if the rectangle does not define a valid crop region.
    """
    box = rect_to_pixel_box(rect, image.width, image.height)
    crop = image.crop(box.as_tuple())
    crop.load()  # PIL crops are lazy; force a real, independent copy.
    return crop