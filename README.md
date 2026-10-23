# PlateChar Annotator

PlateChar Annotator is a desktop application for extracting the seven characters of a license plate from an image. It displays an image, places one editable rectangle at each character position, and saves each selected crop as an individual PNG file.

## Features

- Open PNG, JPEG, and WebP images.
- Move through supported images in the current folder using **Previous image** and **Next image**. Files are ordered naturally, so `image2` comes before `image10`.
- Zoom with the mouse wheel and pan with the middle mouse button or scrollbars.
- Place seven numbered rectangles over the currently visible part of the image. Drag a rectangle to move it, or drag its edges and handles to resize it.
- Lock rectangle proportions with the **W:H** fields. Leave either field empty to resize freely.
- Adjust the row size and move all rectangles together with the **Size**, **Pan H**, and **Pan V** sliders.
- Delete a selected rectangle with **Delete selected**, the **Delete** key, or **Backspace**. A deleted position is skipped when saving; the remaining positions keep their original numbers.
- Enter plate characters and save one crop per non-empty character position.
- See an **Already processed** indicator when all planned output files for an image exist during the current app session.

## Requirements

- Python 3.10 or newer
- pip

The application uses PySide6 for its desktop interface and Pillow for image loading and cropping.

## Install and run

From the project directory, create and activate a virtual environment, install the dependencies, and launch the app:

```sh
python -m venv .venv
```

Linux or macOS:

```sh
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Then, on any platform:

```sh
pip install -r requirements.txt
python main.py
```

## Typical workflow

1. Click **Open image…** and choose a plate image. The image is fitted to the window; its path and pixel dimensions appear above it.
2. Zoom and pan to the plate area if needed. Click **Place rectangles** to create seven numbered rectangles in a row over the visible image area.
3. Adjust the row with the **Size**, **Pan H**, and **Pan V** sliders. Move or resize individual rectangles with the mouse. If needed, set **W:H** to constrain the rectangle proportions.
4. Delete any character position that should not produce a crop. Rectangle numbers are fixed and are not reassigned when other rectangles are deleted.
5. Enter the plate characters in the **Plate** field from left to right. The first character corresponds to rectangle 1, the second to rectangle 2, and so on. Use a space for a blank position. Missing trailing characters are also skipped.
6. Click **Select destination folder…** and choose where to write the crops.
7. Click **Save characters…**. If any planned output names already exist, choose **Overwrite All**, **Skip All**, or **Cancel**.
8. Use **Previous image** or **Next image** to continue through images in the same folder. The plate text and destination folder remain selected while navigating; rectangles are cleared for each newly opened image.

For example, with `ABCDEFG` entered, deleting rectangle 3 skips `C`. Deleting rectangles 3 and 5 skips `C` and `E`; positions 4, 6, and 7 still map to `D`, `F`, and `G` respectively.

## Rectangle and crop behavior

- Rectangles are numbered 1–7 from left to right. They start as a touching row centered in the currently visible image region. Clicking **Re-place rectangles** creates a fresh row in the current view.
- The **Size** slider ranges from 10% to 100% of the largest row that fits in the visible area. It scales the current layout around rectangle 1’s upper-left corner and keeps the group inside the image.
- The default aspect ratio is 9:16. It affects placement and resizing when both **W** and **H** contain positive numbers. Values can use `.` or `,` as the decimal separator. Changing the fields does not reshape existing rectangles immediately; resizing a rectangle applies the new ratio.
- Individual rectangles can move and resize only within the image. Their minimum size is 2×2 pixels.
- Zoom changes the display only; crop coordinates remain tied to the original image pixels. Crops are not resized or filtered. Rectangle edges are rounded to pixel boundaries and clamped to the source image.
- The source image is decoded as stored; EXIF orientation is not applied. Some unusual image modes may be converted for display, while cropping uses the decoded source pixels.

## Output files

Each crop is saved as a PNG in the selected destination folder. Its filename follows this pattern:

```text
{YYMMDDHHMMSS_microseconds}_{source_stem}_{full_plate}_{position}_{character}.png
```

The timestamp is placed first and is made unique within the save batch, so filenames sort in crop creation order. Every filename includes the complete text from the **Plate** field, the crop's 1-based position, and the character label. Spaces in the plate text represent blank positions and appear as underscores in filenames. Characters that are invalid in common filenames are also replaced with underscores.

Existing files are never overwritten without a prompt. **Overwrite All** replaces the planned files that already exist; **Skip All** keeps them and continues with other planned crops; **Cancel** stops the save. The **Already processed** indicator is kept in temporary memory for the current app session and is cleared when the application closes.

## Local defaults

The optional `.local_config.json` file lets you set per-checkout defaults. Start with the example:

```sh
cp .local_config.json.example .local_config.json
```

The file is excluded from Git, so local settings are not committed. Example:

```json
{
  "aspect_ratio": {
    "width": 9,
    "height": 16
  },
  "rectangle_size_fraction": 0.7,
  "group_pan_range_fraction": 0.1,
  "zoom_step_fraction": 0.07
}
```

| Setting | Purpose | Valid values and fallback |
| --- | --- | --- |
| `aspect_ratio.width`, `aspect_ratio.height` | Default **W:H** placement and resize ratio | Both must be positive finite numbers; defaults to 9:16 if missing or invalid. |
| `rectangle_size_fraction` | Initial position of the **Size** slider and row size when rectangles are placed | From `0.1` to `1.0`; default `0.7`. |
| `group_pan_range_fraction` | Maximum **Pan H** and **Pan V** travel from the slider center, as a fraction of image dimensions | Greater than `0` and at most `1`; default `0.1`. |
| `zoom_step_fraction` | Wheel zoom change per standard wheel notch | Greater than `0` and at most `0.5`; default `0.05`. |

Missing or invalid settings use their fallback values. The **W:H** fields can still be changed in the app for the current session.

## Development

Install development dependencies and run the automated tests with:

```sh
pip install -r requirements-dev.txt
python -m pytest
```

The tests cover crop extraction, rectangle layout and resize math, aspect-ratio handling, filename generation, and save planning. The graphical workflow can also be checked manually by opening an image, placing and editing rectangles, deleting positions, and saving crops to a temporary folder.
