# PlateChar Annotator

Desktop tool for manually extracting individual characters from license plate images.

**Current status:** Stage 6 (saving) with zoom, on-demand rectangle placement and an optional aspect-ratio lock.

## Install

    python -m venv .venv
    # Linux/macOS: source .venv/bin/activate
    # Windows:     .venv\Scripts\activate
    pip install -r requirements.txt

## Run

    python main.py

## Run the tests

    pip install -r requirements-dev.txt
    python -m pytest

## How to test Stage 1

1. Run `python main.py`. The window should open.
2. Click **Open image…** and pick a PNG, JPEG, or WebP file. The image should appear scaled to fit, and the label should show its path and original size.
3. Resize the window. The image should rescale and keep its aspect ratio.
4. Open a second image. It should replace the first without restarting.
5. Open a non-image file (choose "All files" in the dialog). An error message should appear and the previous image should remain.

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

## How to test zoom and on-demand rectangles

1. Open an image. No rectangles should appear, and the image should fit the window.
2. Scroll the mouse wheel over the plate area (or click **Zoom +**). The image should zoom toward the cursor, keeping its aspect ratio.
3. Middle-drag (or use the scrollbars if visible) to pan to the part of interest.
4. Click **Place rectangles**. All seven rectangles should appear **complete inside the currently visible area**, ready to be dragged onto the characters. The zoom level must not change.
5. Zoom or pan elsewhere and click **Re-place rectangles**. The seven rectangles should be laid out again inside the new visible area.
6. Click **Fit**. The image should return to fitting the window.
7. Resize the window after zooming. The zoom level must be kept until **Fit** is used or another image is opened.
8. Open another image. The rectangles must disappear and be reset, and **Place rectangles** must create a fresh layout for the new image.

## How to test Stage 6

1. Open an image, enter `ABC1D23` in the **Plate** field, and select a destination folder.
2. Click **Save characters…**. The status bar should report that 7 crops were saved, and the folder should contain `0001_video_00-01-23.450_A.png` … `0001_video_00-01-23.450_3.png`, each with the same pixel dimensions as its rectangle.
3. Save again. A dialog should warn that the files already exist, offering **Overwrite All**, **Skip All**, and **Cancel**. Try each option.
4. Clear the plate field and save. An error must appear and no files may change.
5. Enter `AB 1D23` and save to a fresh folder. Only 6 files should appear, for positions 1, 2, 4, 5, 6, 7 (`A`, `B`, `1`, `D`, `2`, `3`). The blank position must not shift the others.
6. Enter a plate containing a filename-invalid character (e.g. `A/B1D23`) and save. The output filename must use an underscore in place of the invalid character.
7. Try saving without selecting a destination folder. An error must appear.

## How to test the aspect-ratio lock

1. Open an image and click **Place rectangles**. Leave the **W** and **H** fields empty and resize a rectangle by a corner. It must resize freely.
2. Enter `1` in **W** and `2` in **H**. Resize a rectangle by dragging a corner. The opposite corner must stay fixed, and the rectangle must keep a width:height ratio of 1:2 throughout the drag.
3. Drag a side edge (left, right, top or bottom). The opposite edge must stay fixed, and the other dimension must follow the ratio, staying centered on the rectangle.
4. Drag past the image border or shrink the rectangle to the minimum. It must stop at the limit without breaking the ratio.
5. Move a rectangle by its body. Moving must not change its shape.
6. Change the ratio (for example `3` and `1`) while a rectangle is selected. Its shape must not change by itself; it should snap to the new ratio the first time you resize it.
7. Use a decimal ratio such as `2,5` and `5` (a comma works as well as a period). Then clear either field. Resizing must become free again.

## Limitations and notes

- EXIF orientation is deliberately not applied, so displayed pixels match the raw pixels used for cropping in later stages.
- Images with unusual modes (e.g. 16-bit grayscale) are converted to 8-bit RGBA for display only; the original is kept as decoded.
- Rectangle geometry is stored in original-image pixels and is reset every time an image is opened. Rectangles are hidden until **Place rectangles** is clicked, which lays all seven out inside the currently visible (possibly zoomed) area; clicking it again re-places them in the new view, discarding manual adjustments. Whether positions should carry over between images is left for a later stage.
- Wheel zoom centers on the cursor and middle-drag pans, so the part of interest can be brought into view before placing the rectangles.
- Rectangles are kept inside the image and cannot be smaller than 2×2 pixels. They are edited with the mouse only (no keyboard nudging yet).
- The aspect-ratio lock (**W** and **H** fields) applies only to resizing, and only when both fields hold a positive number (`.` or `,` as decimal separator). Changing the ratio does not reshape existing rectangles; a rectangle snaps to the ratio the next time it is resized. **Place rectangles** ignores the ratio.
- Zoom is display-only: it never changes the stored rectangle coordinates or the saved crops.
- Crops cover whole pixels: each rectangle edge is rounded to the nearest pixel (halves round up) and clamped to the image. The crop itself is never resized or filtered.
- Output files are always PNG, named `{source_stem}_{character}.png`. Filename-invalid characters (such as `/`, `?`, `*`) become underscores; letters and digits keep their labels.
- Existing files are never overwritten silently: saving stops and asks to overwrite all, skip all, or cancel. There is no per-file choice, and skipping some positions is done via spaces in the plate field.
- The plate field is not cleared after a successful save. Clearing it after saving is deferred to the workflow-refinement stage.
- Automated tests cover the non-GUI logic and the pure resize math (`crop_service`, `filename_service`, `save_service`, `aspect_ratio`, and the locked-resize function in `rect_item`); GUI behavior is checked manually with the steps above.
