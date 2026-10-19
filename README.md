# PlateChar Annotator

Desktop tool for manually extracting individual characters from license plate images.

**Current status:** Stage 5 (crop extraction and preview).

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

1. Open an image. Seven rectangles, numbered 1 to 7 from left to right, should appear over it, each in a different color.
2. Resize the window. The rectangles must stay aligned with the same parts of the image, and their outlines must keep a constant thickness.
3. Open an image with different dimensions. The rectangles should be recalculated for the new image.

## How to test Stage 4

1. Click rectangle 3. It should get a thicker outline, a stronger tint, and eight small handles.
2. Drag its body. It should move with the cursor; its number must stay 3 and the other rectangles must not move.
3. Drag an edge or a corner. It should resize, and the cursor should change shape near edges and corners.
4. Drag or resize past the image border. The rectangle must stop at the border, and it must stop shrinking at a very small size.
5. Resize the window, then drag again. The rectangle must still follow the cursor exactly.
6. Click an empty area of the image. The selection should clear.

## How to test Stage 5

1. Click rectangle 3. The **Crop preview** panel on the right should show only the pixels inside that rectangle, with a caption giving its size in original pixels.
2. Drag and resize the rectangle. The preview must update while you do so.
3. Open an image much larger than the window and click a rectangle. The caption must report the size in original pixels, not on-screen pixels, and must not change when you resize the window.
4. Click an empty area of the image. The preview should clear.
5. Open another image. The preview should clear.

## Limitations and notes

- EXIF orientation is deliberately not applied, so displayed pixels match the raw pixels used for cropping in later stages.
- Images with unusual modes (e.g. 16-bit grayscale) are converted to 8-bit RGBA for display only; the original is kept as decoded.
- Rectangle geometry is stored in original-image pixels and is reset to the default layout every time an image is opened. Whether positions should carry over between images is left for a later stage.
- Rectangles are kept inside the image and cannot be smaller than 2×2 pixels. They are edited with the mouse only (no keyboard nudging yet).
- Crops cover whole pixels: each rectangle edge is rounded to the nearest pixel (halves round up) and clamped to the image. The crop preview is enlarged or reduced for display only; the crop itself is never resized or filtered.
- Automated tests cover the non-GUI logic only (`crop_service`); GUI behavior is checked manually with the steps above.
- Saving is intentionally not implemented yet. The plate field is not validated until saving exists (Stage 6).
