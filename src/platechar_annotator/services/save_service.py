"""Save validation and file persistence for character crops.

All validation happens before any file is written, so a failure cannot leave a
partially completed save behind. No GUI dependencies.
"""

import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Sequence

from PIL import Image

from platechar_annotator.models.selection import CharacterRect
from platechar_annotator.services.crop_service import CropError, crop_character
from platechar_annotator.services.filename_service import destination_path
from platechar_annotator.services.image_service import LoadedImage

CHARACTER_COUNT = 7


class SaveError(Exception):
    """Raised when the save cannot proceed due to invalid input."""


@dataclass(frozen=True)
class PlannedCrop:
    """One crop ready to be written to disk."""

    index: int
    """Rectangle / character position, 1-based from left to right."""

    character: str
    """The character label used in the output filename."""

    crop: Image.Image
    """Extracted pixels, in original resolution and mode."""

    destination: Path
    """Where the crop will be written."""

    exists: bool
    """True if a file already sat at ``destination`` when the plan was built."""


def _positions_to_save(plate_text: str) -> list[tuple[int, str]]:
    """Map plate text positions to the rectangles that will be saved.

    Position ``i`` (1-based) pairs with rectangle ``i``. Positions past the
    end of the text, or holding whitespace, are empty and skipped. Blank
    positions never shift later characters.
    """
    planned: list[tuple[int, str]] = []
    for position in range(1, CHARACTER_COUNT + 1):
        if position - 1 >= len(plate_text):
            continue
        character = plate_text[position - 1]
        if character.isspace():
            continue
        planned.append((position, character))
    return planned


def prepare_save(
    image: LoadedImage | None,
    plate_text: str,
    rectangles: Sequence[CharacterRect],
    destination_folder: Path | str | None,
    *,
    timestamp: str | None = None,
) -> list[PlannedCrop]:
    """Validate everything and build the save plan without writing files.

    Raises:
        SaveError: if no image is loaded, the plate field is empty, the
            destination folder is missing or unwritable, or a rectangle is
            missing for a position to save.
        CropError: if a rectangle does not define a valid crop region.
    """
    if image is None or image.pixels is None:
        raise SaveError("No image has been loaded. Open an image first.")

    if not plate_text or not plate_text.strip():
        raise SaveError("Enter the plate characters before saving.")

    if destination_folder is None:
        raise SaveError("No destination folder has been selected.")
    folder = Path(destination_folder)
    if not folder.exists():
        raise SaveError(f"Destination folder does not exist: {folder}")
    if not folder.is_dir():
        raise SaveError(f"Destination is not a folder: {folder}")
    if not os.access(folder, os.W_OK):
        raise SaveError(f"Destination folder is not writable: {folder}")

    positions = _positions_to_save(plate_text)
    if not positions:
        raise SaveError(
            "Nothing to save: every character position is empty. "
            "Enter at least one character, or use spaces for empty positions."
        )

    rects_by_index = {rect.index: rect for rect in rectangles}

    crops: list[tuple[int, str, Image.Image]] = []
    for index, character in positions:
        rect = rects_by_index.get(index)
        if rect is None:
            continue  # A deleted rectangle leaves that character position empty.
        crop = crop_character(image.pixels, rect)  # CropError propagates.
        crops.append((index, character, crop))

    if not crops:
        raise SaveError(
            "Nothing to save: no character positions have a rectangle."
        )

    # Position is added only when repeated or sanitized labels collide. Give
    # every crop its own increasing local timestamp so the prefixes sort too.
    plain_names = [
        destination_path(folder, image.path, character, timestamp="").name.casefold()
        for _, character, _ in crops
    ]
    name_counts = Counter(plain_names)
    planned: list[PlannedCrop] = []
    last_timestamp: datetime | None = None
    for index, character, crop in crops:
        if timestamp is None:
            current_timestamp = datetime.now()
            if last_timestamp is not None and current_timestamp <= last_timestamp:
                current_timestamp = last_timestamp + timedelta(microseconds=1)
            crop_timestamp = current_timestamp.strftime("%y%m%d%H%M%S_%f")
            last_timestamp = current_timestamp
        else:
            crop_timestamp = timestamp
        plain = destination_path(folder, image.path, character, timestamp="")
        destination = destination_path(
            folder,
            image.path,
            character,
            timestamp=crop_timestamp,
            position=index if name_counts[plain.name.casefold()] > 1 else None,
        )
        planned.append(
            PlannedCrop(
                index=index,
                character=character,
                crop=crop,
                destination=destination,
                exists=destination.exists(),
            )
        )
    return planned


def save_crops(planned: Sequence[PlannedCrop], overwrite_existing: bool) -> list[Path]:
    """Write the planned crops as PNG files.

    Existing files are skipped unless ``overwrite_existing`` is true. The
    existence check is done at write time, so files created after planning
    are still honoured. The crop pixels are never resized or filtered.

    Returns the list of paths that were written.
    """
    saved: list[Path] = []
    for crop in planned:
        if crop.destination.exists() and not overwrite_existing:
            continue
        crop.crop.save(crop.destination, format="PNG")
        saved.append(crop.destination)
    return saved
