"""Tests for save planning and file persistence (no GUI needed)."""

from pathlib import Path

import pytest
from PIL import Image

from platechar_annotator.models.selection import (
    CharacterRect,
    create_default_rectangles,
)
from platechar_annotator.services.crop_service import CropError
from platechar_annotator.services.image_service import LoadedImage
from platechar_annotator.services.save_service import (
    SaveError,
    prepare_save,
    save_crops,
)

PLATE_STEM = "0001_video_00-01-23.450"


def make_loaded_image(size: tuple[int, int], color: int = 7) -> LoadedImage:
    """A LoadedImage whose pixels are a plain L-mode image."""
    return LoadedImage(
        path=Path(f"{PLATE_STEM}.png"), pixels=Image.new("L", size, color)
    )


def make_gradient_image(size: tuple[int, int]) -> LoadedImage:
    """RGB image where pixel (x, y) is (x, y, 0), so crops are easy to verify."""
    width, height = size
    image = Image.new("RGB", size)
    image.putdata([(x, y, 0) for y in range(height) for x in range(width)])
    return LoadedImage(path=Path(f"{PLATE_STEM}.png"), pixels=image)


def make_rect(
    x: float, y: float, width: float, height: float, index: int = 1
) -> CharacterRect:
    return CharacterRect(index=index, x=x, y=y, width=width, height=height)


def test_positions_are_mapped_left_to_right_skipping_blanks(tmp_path):
    folder = tmp_path / "out"
    folder.mkdir()
    image = make_loaded_image((200, 100))

    planned = prepare_save(
        image, "AB 1D23", create_default_rectangles(200, 100), folder
    )

    assert [crop.index for crop in planned] == [1, 2, 4, 5, 6, 7]
    assert [crop.character for crop in planned] == ["A", "B", "1", "D", "2", "3"]
    assert all(not crop.exists for crop in planned)


def test_short_plate_only_uses_leading_positions(tmp_path):
    folder = tmp_path / "out"
    folder.mkdir()
    image = make_loaded_image((200, 100))

    planned = prepare_save(image, "AB", create_default_rectangles(200, 100), folder)

    assert [crop.index for crop in planned] == [1, 2]


def test_empty_plate_field_raises(tmp_path):
    image = make_loaded_image((200, 100))
    with pytest.raises(SaveError):
        prepare_save(image, "", create_default_rectangles(200, 100), tmp_path / "out")


def test_whitespace_only_plate_raises(tmp_path):
    image = make_loaded_image((200, 100))
    with pytest.raises(SaveError):
        prepare_save(
            image, "   ", create_default_rectangles(200, 100), tmp_path / "out"
        )


def test_plate_with_all_positions_empty_raises(tmp_path):
    image = make_loaded_image((200, 100))
    with pytest.raises(SaveError):
        prepare_save(
            image, "       ", create_default_rectangles(200, 100), tmp_path / "out"
        )


def test_no_image_raises(tmp_path):
    with pytest.raises(SaveError):
        prepare_save(
            None, "ABC1D23", create_default_rectangles(200, 100), tmp_path / "out"
        )


def test_missing_folder_raises(tmp_path):
    image = make_loaded_image((200, 100))
    with pytest.raises(SaveError):
        prepare_save(
            image, "ABC1D23", create_default_rectangles(200, 100), tmp_path / "missing"
        )


def test_file_as_destination_folder_raises(tmp_path):
    image = make_loaded_image((200, 100))
    not_a_folder = tmp_path / "file.txt"
    not_a_folder.write_text("x")
    with pytest.raises(SaveError):
        prepare_save(
            image, "ABC1D23", create_default_rectangles(200, 100), not_a_folder
        )


def test_invalid_rectangle_propagates_croperror(tmp_path):
    folder = tmp_path / "out"
    folder.mkdir()
    image = make_loaded_image((100, 100))
    rectangles = [make_rect(10, 10, 20, 20, index=i) for i in range(1, 8)]
    rectangles[2] = make_rect(500, 10, 20, 20, index=3)
    with pytest.raises(CropError):
        prepare_save(image, "ABC1D23", rectangles, folder)


def test_crops_are_taken_from_the_right_region(tmp_path):
    folder = tmp_path / "out"
    folder.mkdir()
    image = make_gradient_image((200, 100))
    rectangles = [
        make_rect(10, 20, 5, 4, index=1),
        make_rect(30, 40, 5, 4, index=2),
        make_rect(10, 20, 5, 4, index=3),
        make_rect(10, 20, 5, 4, index=4),
        make_rect(10, 20, 5, 4, index=5),
        make_rect(10, 20, 5, 4, index=6),
        make_rect(10, 20, 5, 4, index=7),
    ]

    planned = prepare_save(image, "AB1D23", rectangles, folder)

    assert planned[0].crop.size == (5, 4)
    assert planned[0].crop.getpixel((0, 0)) == (10, 20, 0)
    assert planned[0].crop.getpixel((4, 3)) == (14, 23, 0)


def test_save_crops_writes_png_files_without_resampling(tmp_path):
    folder = tmp_path / "out"
    folder.mkdir()
    image = make_loaded_image((200, 100))
    planned = prepare_save(
        image, "ABC1D23", create_default_rectangles(200, 100), folder
    )

    saved = save_crops(planned, overwrite_existing=True)

    assert len(saved) == 7
    for crop in planned:
        assert crop.destination.exists()
        with Image.open(crop.destination) as written:
            assert written.format == "PNG"
            assert written.size == crop.crop.size
            assert written.mode == crop.crop.mode
    assert saved == [crop.destination for crop in planned]


def test_existing_files_are_skipped_without_overwrite(tmp_path):
    folder = tmp_path / "out"
    folder.mkdir()
    image = make_loaded_image((200, 100))
    planned = prepare_save(image, "A", create_default_rectangles(200, 100), folder)

    assert save_crops(planned, overwrite_existing=True) == [planned[0].destination]

    # The file now exists; saving again without overwriting must skip it.
    original_bytes = planned[0].destination.read_bytes()
    assert save_crops(planned, overwrite_existing=False) == []
    assert planned[0].destination.read_bytes() == original_bytes


def test_existing_files_are_overwritten_when_requested(tmp_path):
    folder = tmp_path / "out"
    folder.mkdir()
    image = make_loaded_image((200, 100))
    planned = prepare_save(image, "A", create_default_rectangles(200, 100), folder)
    planned[0].destination.write_bytes(b"old")

    saved = save_crops(planned, overwrite_existing=True)

    assert saved == [planned[0].destination]
    assert planned[0].destination.read_bytes() != b"old"


def test_existing_flag_is_set_when_file_already_exists(tmp_path):
    folder = tmp_path / "out"
    folder.mkdir()
    image = make_loaded_image((200, 100))
    first = prepare_save(image, "A", create_default_rectangles(200, 100), folder)
    save_crops(first, overwrite_existing=True)

    second = prepare_save(image, "A", create_default_rectangles(200, 100), folder)

    assert second[0].exists is True
