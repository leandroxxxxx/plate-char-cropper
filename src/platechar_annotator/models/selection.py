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


def create_default_rectangles(
    image_width: int, image_height: int
) -> list[CharacterRect]:
    """Create the seven rectangles as an evenly spaced row, left to right.

    Raises:
        ValueError: if the image dimensions are not positive.
    """
    if image_width <= 0 or image_height <= 0:
        raise ValueError("Image dimensions must be positive.")

    margin_x = image_width * _MARGIN_X_RATIO
    slot_width = (image_width - 2 * margin_x) / CHARACTER_COUNT
    rect_width = slot_width * (1 - _GAP_RATIO)
    rect_y = image_height * _MARGIN_Y_RATIO
    rect_height = image_height * (1 - 2 * _MARGIN_Y_RATIO)

    return [
        CharacterRect(
            index=position + 1,
            x=margin_x + position * slot_width + (slot_width - rect_width) / 2,
            y=rect_y,
            width=rect_width,
            height=rect_height,
        )
        for position in range(CHARACTER_COUNT)
    ]