"""Tests for output filename construction and sanitization (no GUI needed)."""

from pathlib import Path

import pytest

from platechar_annotator.services.filename_service import (
    build_filename,
    destination_path,
    sanitize_character_label,
    source_stem,
)


def test_source_stem_removes_only_the_final_extension():
    assert (
        source_stem(Path("0001_video_00-01-23.450.png"))
        == "0001_video_00-01-23.450"
    )
    assert source_stem("archive.tar.gz") == "archive.tar"


def test_build_filename_follows_the_documented_convention():
    stem = source_stem(Path("0001_video_00-01-23.450.png"))
    assert build_filename(stem, "A", "261020101010_123456", 1) == "261020101010_123456_0001_video_00-01-23.450_1_A.png"


@pytest.mark.parametrize("character", ["A", "b", "7", "-", "Á"])
def test_standard_plate_characters_pass_through_unchanged(character):
    assert sanitize_character_label(character) == character


@pytest.mark.parametrize(
    "character", ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
)
def test_illegal_filename_characters_are_replaced(character):
    assert sanitize_character_label(character) == "_"


def test_control_characters_are_replaced():
    assert sanitize_character_label("A\x00B") == "A_B"


def test_empty_or_all_invalid_label_becomes_underscore():
    assert sanitize_character_label("") == "_"
    assert sanitize_character_label("/") == "_"


def test_destination_path_is_inside_the_folder_with_png_extension():
    path = destination_path(
        Path("/out"), Path("0001_video_00-01-23.450.png"), "B", "261020101010_123456", 2
    )
    assert path == Path("/out/261020101010_123456_0001_video_00-01-23.450_2_B.png")
    assert path.suffix == ".png"
