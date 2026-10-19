"""Data structures for the seven character rectangles.

Rectangle geometry is stored in original-image pixel coordinates, so it is
independent of how the image is scaled for display.
"""

from dataclasses import dataclass

CHARACTER_COUNT = 7

# Default layout, as fractions of the image size.
_MARGIN_X_RATIO = 0.05
_MARGIN_Y_RATIO = 0.15
_GAP_RATIO = 0.10  # Gap between neighbours, as a fraction of the slot width.


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
    region_x: float, region_y: float, region_width: float, region_height: float
) -> list[CharacterRect]:
    """Create the seven rectangles as an evenly spaced row inside a region.

    The region is given in original-image pixels (for example the part of the
    image currently visible when zoomed in). Rectangles are numbered 1 to 7
    from left to right and all lie fully inside the region.

    Raises:
        ValueError: if the region dimensions are not positive.
    """
    if region_width <= 0 or region_height <= 0:
        raise ValueError("Region dimensions must be positive.")

    margin_x = region_width * _MARGIN_X_RATIO
    slot_width = (region_width - 2 * margin_x) / CHARACTER_COUNT
    rect_width = slot_width * (1 - _GAP_RATIO)
    rect_y = region_y + region_height * _MARGIN_Y_RATIO
    rect_height = region_height * (1 - 2 * _MARGIN_Y_RATIO)

    return [
        CharacterRect(
            index=position + 1,
            x=region_x
            + margin_x
            + position * slot_width
            + (slot_width - rect_width) / 2,
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