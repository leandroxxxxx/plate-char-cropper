"""Tests for plates with repeated or colliding characters (no GUI needed)."""

from pathlib import Path
import re

from PIL import Image

from platechar_annotator.models.selection import CharacterRect
from platechar_annotator.services.filename_service import build_filename
from platechar_annotator.services.image_service import LoadedImage
from platechar_annotator.services.save_service import prepare_save, save_crops


def make_image(folder: Path) -> LoadedImage:
    """A 70x10 image; the source file itself does not need to exist."""
    return LoadedImage(
        path=folder / "0001_video.png", pixels=Image.new("RGB", (70, 10))
    )


def make_rectangles() -> list[CharacterRect]:
    """Seven 10x10 rectangles side by side, indices 1 to 7."""
    return [
        CharacterRect(index=i, x=(i - 1) * 10, y=0, width=10, height=10)
        for i in range(1, 8)
    ]


def planned_names(tmp_path: Path, plate: str) -> list[str]:
    planned = prepare_save(make_image(tmp_path), plate, make_rectangles(), tmp_path)
    return [crop.destination.name for crop in planned]


def test_each_crop_has_its_own_increasing_timestamp(tmp_path):
    names = planned_names(tmp_path, "ABC1D23")
    timestamps = ["_".join(name.split("_")[:2]) for name in names]
    assert len(set(timestamps)) == len(names)
    assert timestamps == sorted(timestamps)
    assert all(re.fullmatch(r"\d{12}_\d{6}", stamp) for stamp in timestamps)
    assert all(not re.search(r"_\d+_[^_]+\.png$", name) for name in names)


def test_repeated_character_keeps_both_positions(tmp_path):
    names = planned_names(tmp_path, "ABC1C23")
    assert "_3_C.png" in names[2]
    assert "_5_C.png" in names[4]


def test_names_differing_only_by_case_get_distinct_positions(tmp_path):
    names = planned_names(tmp_path, "aA")
    assert names[0] != names[1]


def test_characters_sanitized_to_the_same_label_get_distinct_positions(tmp_path):
    names = planned_names(tmp_path, "?*")
    assert names[0] != names[1]


def test_blank_positions_do_not_shift_positions_in_names(tmp_path):
    names = planned_names(tmp_path, "A A")
    assert "_1_A.png" in names[0]
    assert "_3_A.png" in names[1]


def test_every_crop_of_a_repeated_character_plate_is_written(tmp_path):
    planned = prepare_save(
        make_image(tmp_path), "ABC1C23", make_rectangles(), tmp_path
    )
    saved = save_crops(planned, overwrite_existing=False)
    assert len(saved) == 7
    assert len(list(tmp_path.glob("*.png"))) == 7


def test_build_filename_includes_timestamp_and_position():
    assert build_filename("0001_video", "C", "261020101010_123456", 3) == "261020101010_123456_0001_video_3_C.png"
