"""Tests for plates with repeated or colliding characters (no GUI needed)."""

from pathlib import Path

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


def test_distinct_characters_keep_the_plain_names(tmp_path):
    assert planned_names(tmp_path, "ABC1D23") == [
        "0001_video_A.png",
        "0001_video_B.png",
        "0001_video_C.png",
        "0001_video_1.png",
        "0001_video_D.png",
        "0001_video_2.png",
        "0001_video_3.png",
    ]


def test_repeated_character_gets_its_position_in_the_name(tmp_path):
    assert planned_names(tmp_path, "ABC1C23") == [
        "0001_video_A.png",
        "0001_video_B.png",
        "0001_video_3_C.png",
        "0001_video_1.png",
        "0001_video_5_C.png",
        "0001_video_2.png",
        "0001_video_3.png",
    ]


def test_names_differing_only_by_case_are_disambiguated(tmp_path):
    assert planned_names(tmp_path, "aA") == [
        "0001_video_1_a.png",
        "0001_video_2_A.png",
    ]


def test_characters_sanitized_to_the_same_label_are_disambiguated(tmp_path):
    assert planned_names(tmp_path, "?*") == [
        "0001_video_1__.png",
        "0001_video_2__.png",
    ]


def test_blank_positions_do_not_shift_positions_in_names(tmp_path):
    assert planned_names(tmp_path, "A A") == [
        "0001_video_1_A.png",
        "0001_video_3_A.png",
    ]


def test_every_crop_of_a_repeated_character_plate_is_written(tmp_path):
    planned = prepare_save(
        make_image(tmp_path), "ABC1C23", make_rectangles(), tmp_path
    )
    saved = save_crops(planned, overwrite_existing=False)
    assert len(saved) == 7
    assert len(list(tmp_path.glob("*.png"))) == 7


def test_build_filename_position_variant():
    assert build_filename("0001_video", "C") == "0001_video_C.png"
    assert build_filename("0001_video", "C", position=3) == "0001_video_3_C.png"