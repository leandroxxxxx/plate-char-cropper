"""Image loading and access to the original image data.

This module has no GUI dependencies. The loaded image is kept exactly as
decoded from disk so later stages can crop from the original pixels.
"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError


class ImageLoadError(Exception):
    """Raised when a file cannot be loaded as an image."""


@dataclass(frozen=True)
class LoadedImage:
    """An image loaded from disk, with its original pixel data untouched."""

    path: Path
    pixels: Image.Image

    @property
    def width(self) -> int:
        return self.pixels.width

    @property
    def height(self) -> int:
        return self.pixels.height


def load_image(path: Path) -> LoadedImage:
    """Load an image file fully into memory.

    Raises:
        ImageLoadError: if the file is missing, unreadable, or not a
            supported image.
    """
    try:
        with Image.open(path) as opened:
            opened.load()  # Force decoding so errors surface here.
            pixels = opened.copy()
    except FileNotFoundError as exc:
        raise ImageLoadError(f"File not found: {path}") from exc
    except UnidentifiedImageError as exc:
        raise ImageLoadError(f"Not a supported image file: {path.name}") from exc
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ImageLoadError(f"Could not read '{path.name}': {exc}") from exc

    return LoadedImage(path=path, pixels=pixels)