# PlateChar Annotator

Desktop tool for manually extracting individual characters from license plate images.

**Current status:** Stage 6 (saving) with same-folder image navigation, zoom, on-demand rectangle placement, group movement, a size slider and an optional aspect-ratio lock.

## Install

    python -m venv .venv
    # Linux/macOS: source .venv/bin/activate
    # Windows:     .venv\Scripts\activate
    pip install -r requirements.txt

## Run

    python main.py

## Local defaults

Copy `.local_config.json.example` to `.local_config.json` to set defaults for this checkout. The file is ignored by Git. The default aspect ratio is 9:16; change `width` and `height` in the local file to use another ratio. `group_pan_range_fraction` sets the maximum travel from the slider center as a fraction of the image size; the default `0.1` gives each slider a ±10% range with finer movement. `zoom_step_fraction` controls wheel zoom speed per standard wheel notch; its default `0.05` changes zoom by about 5% per notch. If either setting is missing or invalid, the app uses its default.

## Run the tests

    pip install -r requirements-dev.txt
    python -m pytest

## How to test Stage 1

1. Run `python main.py`. The window should open.
2. Click **Open image…** and pick a PNG, JPEG, or WebP file. The image should appear scaled to fit, and the label should show its path and original size.
3. Resize the window. The image should rescale and keep its aspect ratio.
4. Open a second image. It should replace the first without restarting.
5. Open a non-image file (choose "All files" in the dialog). An error message should appear and the previous image should remain.
6. Open an image in a folder with several PNG, JPEG or WebP images. **Previous image** and **Next image** should navigate in ascending natural filename order (`A0` before `A1`, `image2` before `image10`); each button is disabled at the first or last image.

## How to test Stage 2

1. Type `AB 1D23` in the **Plate** field, including the blank third position.
2. Open another image. The field must keep its exact contents.
3. Click **Select destination folder…** and choose a folder. Its path must appear next to the button.
4. Open another image. The folder must remain selected.
5. Open the folder dialog again and cancel it. The previous folder must remain selected.

## How to test Stage 3

1. Open an image, then click **Place rectangles**. Seven rectangles, numbered 1 to 7 from left to right, should appear over the image, each in a different color.
2. Resize the window. The rectangles must stay aligned with the same parts of the image, and their outlines must keep a constant thickness.
3. Open an image with different dimensions. The rectangles should be recalculated for the new image.

## How to test Stage 4

1. Click rectangle 3. It should get a thicker outline, a stronger tint, and eight small handles.
2. Drag its body. It should move with the cursor; its number must stay 3 and the other rectangles must not move.
3. Drag an edge or a corner. It should resize, and the cursor should change shape near edges and corners.
4. Drag or resize past the image border. The rectangle must stop at the border, and it must stop shrinking at a very small size.
5. Resize the window, then drag again. The rectangle must still follow the cursor exactly.
6. Click an empty area of the image. The selection should clear.

## How to test zoom, the size slider and on-demand rectangles

1. Open an image. No rectangles should appear, and the image should fit the window.
2. Scroll the mouse wheel over the plate area. The image should zoom toward the cursor, keeping its aspect ratio.
3. Middle-drag (or use the scrollbars if visible) to pan to the part of interest.
4. Click **Place rectangles**. Seven rectangles should appear side by side, touching each other, **complete inside the currently visible area**. The zoom level must not change.
5. Move the **Size** slider. All seven rectangles must grow or shrink together while the upper-left corner of rectangle 1 stays fixed. Their relative positions must be preserved.
6. Enter `1` in **W** and `2` in **H**, then click **Re-place rectangles** (or move the slider). Every rectangle must now be twice as tall as wide, in a touching row.
7. Zoom or pan elsewhere and click **Re-place rectangles**. The row should be laid out again inside the new visible area.
8. Resize the window after zooming. The zoom level must be kept until another image is opened.
9. Open another image. The rectangles must disappear and be reset, the image must fit the window, and **Place rectangles** must create a fresh layout for the new image.
10. Use **Move all horizontally** and **Move all vertically** to shift the full group together. The controls must stop the rectangles at the image edges.

## How to test Stage 6

1. Open an image, enter `ABC1D23` in the **Plate** field, and select a destination folder.
2. Click **Save characters…**. The status bar should report that 7 crops were saved. Each output filename starts with its own sortable local timestamp in `YYMMDDHHMMSS_microseconds` format, followed by the source name and character label.
3. Save again. Each crop gets a fresh timestamp, so filenames remain separate.
4. Navigate away and back to the image. A blue **Already processed** label should appear after all planned crops exist. Close and restart the app; the temporary marker should be cleared.
5. Clear the plate field and save. An error must appear and no files may change.
6. Enter `AB 1D23` and save to a fresh folder. Only 6 files should appear, for positions 1, 2, 4, 5, 6, 7 (`A`, `B`, `1`, `D`, `2`, `3`). The blank position must not shift the others.
7. Enter a plate containing a filename-invalid character (e.g. `A/B1D23`) and save. The output filename must use an underscore in place of the invalid character.
8. Try saving without selecting a destination folder. An error must appear.
9. Enter `ABC1C23` (a repeated character) and save to a fresh folder. All 7 files must appear; the two `C` crops must retain position markers `_3_C` and `_5_C`.

## How to test the aspect-ratio lock

1. Open an image and click **Place rectangles**. The default **W** and **H** values are 9 and 16. Clear either field, then resize a rectangle by a corner. It must resize freely.
2. Enter `1` in **W** and `2` in **H**. Resize a rectangle by dragging a corner. The opposite corner must stay fixed, and the rectangle must keep a width:height ratio of 1:2 throughout the drag.
3. Drag a side edge (left, right, top or bottom). The opposite edge must stay fixed, and the other dimension must follow the ratio, staying centered on the rectangle.
4. Drag past the image border or shrink the rectangle to the minimum. It must stop at the limit without breaking the ratio.
5. Move a rectangle by its body. Moving must not change its shape.
6. Change the ratio (for example `3` and `1`) while a rectangle is selected. Its shape must not change by itself; it should snap to the new ratio the first time you resize it.
7. Use a decimal ratio such as `2,5` and `5` (a comma works as well as a period). Then clear either field. Resizing must become free again.

## Limitations and notes

- EXIF orientation is deliberately not applied, so displayed pixels match the raw pixels used for cropping in later stages.
- Images with unusual modes (e.g. 16-bit grayscale) are converted to 8-bit RGBA for display only; the original is kept as decoded.
- Rectangle geometry is stored in original-image pixels and is reset every time an image is opened. Rectangles are hidden until **Place rectangles** is clicked, which lays all seven out as a touching row inside the currently visible (possibly zoomed) area. Clicking **Re-place rectangles** creates a fresh row. The **Size** slider scales the current layout around the upper-left corner of rectangle 1, keeping that point fixed and preserving the other rectangles' relative positions.
- Wheel zoom centers on the cursor and middle-drag pans, so the part of interest can be brought into view before placing the rectangles. There are no zoom or fit buttons: zoom out with the wheel, or open the image again to fit it to the window.
- **Previous image** and **Next image** move through PNG, JPEG and WebP files in the current image's folder in natural filename order. Navigating resets rectangles and fits the new image to the view while keeping the plate field and destination folder.
- Rectangles are kept inside the image and cannot be smaller than 2×2 pixels. They are edited with the mouse only (no keyboard nudging yet).
- The aspect-ratio lock (**W** and **H** fields) applies only when both fields hold a positive number (`.` or `,` as decimal separator). **Place rectangles** and the **Size** slider lay the rectangles out with that ratio, and resizing keeps it. Changing the fields does not reshape rectangles that are already placed; one snaps to the ratio the next time it is resized, or when the row is re-laid.
- The **Size** slider sets the width and height of all seven rectangles together, from 10% to 100% of the largest row that fits the visible area when first placed. Later size changes scale the current layout around rectangle 1's upper-left corner, keeping it fixed and clamping the group to the image bounds. Without a ratio, each initially placed rectangle keeps the proportions of the visible area split into seven columns.
- The adjustment row puts **Zoom (wheel)** first, followed by **Size**, **Pan H**, and **Pan V**. The pan sliders translate the rectangle group together in fine increments, clamped so the rectangles stay inside the image. Their range is set by `group_pan_range_fraction` in the local config. Re-placing the rectangles or opening another image resets both pan controls.
- Zoom is display-only: it never changes the stored rectangle coordinates or the saved crops.
- Crops cover whole pixels: each rectangle edge is rounded to the nearest pixel (halves round up) and clamped to the image. The crop itself is never resized or filtered.
- Output files are always PNG, named `{YYMMDDHHMMSS_microseconds}_{source_stem}_{character}.png`. Each crop gets its own increasing local timestamp, so filename prefixes sort in crop creation order without sequence numbers. A 1-based position is added only when labels repeat or sanitize to the same text within a batch. Filename-invalid characters (such as `/`, `?`, `*`) become underscores; letters and digits keep their labels.
- Existing files are never overwritten silently: saving stops and asks to overwrite all, skip all, or cancel. There is no per-file choice, and skipping some positions is done via spaces in the plate field.
- Images are marked processed in temporary memory for the current app session once all planned crop files exist. A blue **Already processed** label appears when the image is loaded again; restarting the app clears these markers.
- The plate field is not cleared after a successful save. Clearing it after saving is deferred to the workflow-refinement stage.
- Automated tests cover the non-GUI logic and the pure resize math (`crop_service`, `filename_service`, `save_service`, `aspect_ratio`, the rectangle layout in `selection`, and the locked-resize function in `rect_item`); GUI behavior is checked manually with the steps above.
