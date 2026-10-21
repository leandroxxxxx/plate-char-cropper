"""Data structures for the seven character rectangles.

Rectangle geometry is stored in original-image pixel coordinates, so it is
independent of how the image is scaled for display.
"""

import math
from dataclasses import dataclass

CHARACTER_COUNT = 7

# Row size as a fraction of the largest row that fits the region (the UI
# slider moves between MIN and MAX).
MIN_SIZE_FRACTION = 0.1
MAX_SIZE_FRACTION = 1.0
DEFAULT_SIZE_FRACTION = 0.7


@dataclass
class CharacterRect:
    """A rectangle bound to one fixed character position.

    ``index`` is 1-based, left to right, and never changes when the
    rectangle is moved or resized. Geometry is in original-image pixels.
    """

    index: int
    x: float
    y: float
    width: float
    height: float


def create_rectangles_in_region(
    region_x: float,
    region_y: float,
    region_width: float,
    region_height: float,
    aspect_ratio: float | None = None,
    size_fraction: float = DEFAULT_SIZE_FRACTION,
) -> list[CharacterRect]:
    """Create the seven rectangles as a row of touching rectangles in a region.

    The region is given in original-image pixels (for example the part of the
    image currently visible when zoomed in). Rectangles are numbered 1 to 7
    from left to right, all have the same size, touch their neighbours (no gap)
    and are centred in the region.

    ``aspect_ratio`` is width / height of each rectangle. If None, each
    rectangle gets the shape of the region split into seven equal columns.
    ``size_fraction`` scales the row relative to the largest row that fits
    inside the region (1.0 = as large as possible).

    Raises:
        ValueError: if the region dimensions are not positive, the aspect
            ratio is not a positive finite number, or the size fraction is
            outside (0, 1].
    """
    if region_width <= 0 or region_height <= 0:
        raise ValueError("Region dimensions must be positive.")
    if aspect_ratio is not None and not (
        math.isfinite(aspect_ratio) and aspect_ratio > 0
    ):
        raise ValueError("Aspect ratio must be a positive number.")
    if not 0 < size_fraction <= MAX_SIZE_FRACTION:
        raise ValueError("Size fraction must be in (0, 1].")

    ratio = aspect_ratio or region_width / (CHARACTER_COUNT * region_height)
    largest_height = min(
        region_height, region_width / (CHARACTER_COUNT * ratio)
    )
    rect_height = largest_height * size_fraction
    rect_width = rect_height * ratio

    row_x = region_x + (region_width - CHARACTER_COUNT * rect_width) / 2
    rect_y = region_y + (region_height - rect_height) / 2

    return [
        CharacterRect(
            index=position + 1,
            x=row_x + position * rect_width,
            y=rect_y,
            width=rect_width,
            height=rect_height,
        )
        for position in range(CHARACTER_COUNT)
    ]


def create_default_rectangles(
    image_width: int, image_height: int
) -> list[CharacterRect]:
    """Create the seven rectangles as an evenly spaced row over the whole image.

    Raises:
        ValueError: if the image dimensions are not positive.
    """
    if image_width <= 0 or image_height <= 0:
        raise ValueError("Image dimensions must be positive.")
    return create_rectangles_in_region(0, 0, image_width, image_height)