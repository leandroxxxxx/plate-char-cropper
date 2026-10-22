"""Main application window."""

import re
from pathlib import Path

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QFontDatabase, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from platechar_annotator.models.selection import (
    DEFAULT_SIZE_FRACTION,
    MAX_SIZE_FRACTION,
    MIN_SIZE_FRACTION,
    CharacterRect,
    create_rectangles_in_region,
)
from platechar_annotator.services.aspect_ratio import parse_aspect_ratio
from platechar_annotator.services.crop_service import CropError
from platechar_annotator.services.image_service import (
    ImageLoadError,
    LoadedImage,
    load_image,
)
from platechar_annotator.services.local_config import (
    load_default_aspect_ratio,
    load_group_pan_range_fraction,
)
from platechar_annotator.services.save_service import (
    SaveError,
    prepare_save,
    save_crops,
)
from platechar_annotator.ui import dialogs
from platechar_annotator.ui.image_view import ImageView


class MainWindow(QMainWindow):
    """Main window: image view, plate character input, destination folder."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PlateChar Annotator")
        self.resize(1000, 700)

        self._current_image: LoadedImage | None = None
        self._last_directory: Path | None = None
        self._destination_folder: Path | None = None
        self._image_paths: list[Path] = []
        self._image_index: int | None = None
        self._rectangles: list[CharacterRect] = []
        self._rectangles_visible = False
        self._size_anchor_rectangles: list[CharacterRect] = []
        self._size_anchor_value = round(DEFAULT_SIZE_FRACTION * 100)

        self._image_view = ImageView()
        self._image_view.rectangle_changed.connect(self._on_rectangle_changed)

        self._open_button = QPushButton("Open image…")
        self._open_button.clicked.connect(self._on_open_image)

        self._previous_image_button = QPushButton("Previous image")
        self._previous_image_button.setEnabled(False)
        self._previous_image_button.clicked.connect(lambda: self._navigate_image(-1))
        self._next_image_button = QPushButton("Next image")
        self._next_image_button.setEnabled(False)
        self._next_image_button.clicked.connect(lambda: self._navigate_image(1))

        self._place_button = QPushButton("Place rectangles")
        self._place_button.setToolTip(
            "Place the seven character rectangles inside the currently visible area"
        )
        self._place_button.clicked.connect(self._on_place_rectangles)

        self._size_slider = QSlider(Qt.Orientation.Horizontal)
        self._size_slider.setRange(
            round(MIN_SIZE_FRACTION * 100), round(MAX_SIZE_FRACTION * 100)
        )
        self._size_slider.setValue(round(DEFAULT_SIZE_FRACTION * 100))
        self._size_slider.setFixedWidth(120)
        self._size_slider.setToolTip(
            "Size of the seven rectangles (they stay side by side)"
        )
        self._size_slider.valueChanged.connect(self._on_size_changed)

        self._pan_horizontal_slider = self._create_pan_slider("Move all rectangles horizontally")
        self._pan_vertical_slider = self._create_pan_slider("Move all rectangles vertically")
        self._pan_range_fraction = load_group_pan_range_fraction()
        self._pan_horizontal_slider.valueChanged.connect(
            lambda value: self._on_group_pan_changed("x", value)
        )
        self._pan_vertical_slider.valueChanged.connect(
            lambda value: self._on_group_pan_changed("y", value)
        )
        self._pan_last_values = {"x": 0, "y": 0}

        self._save_button = QPushButton("Save characters…")
        self._save_button.clicked.connect(self._on_save)

        self._path_label = QLabel("No image loaded.")
        self._status_label = QLabel("")

        self._plate_input = QLineEdit()
        self._plate_input.setPlaceholderText(
            "Plate characters, e.g. ABC1D23 (use spaces for empty positions)"
        )
        self._plate_input.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )

        self._ratio_width_input = self._create_ratio_input("W")
        self._ratio_height_input = self._create_ratio_input("H")
        default_width, default_height = load_default_aspect_ratio()
        self._ratio_width_input.setText(f"{default_width:g}")
        self._ratio_height_input.setText(f"{default_height:g}")
        self._ratio_width_input.textChanged.connect(self._on_aspect_ratio_changed)
        self._ratio_height_input.textChanged.connect(self._on_aspect_ratio_changed)

        self._folder_button = QPushButton("Select destination folder…")
        self._folder_button.clicked.connect(self._on_select_folder)

        self._folder_label = QLabel("No destination folder selected.")

        toolbar = QHBoxLayout()
        toolbar.addWidget(self._open_button)
        toolbar.addWidget(self._previous_image_button)
        toolbar.addWidget(self._next_image_button)
        toolbar.addWidget(self._place_button)
        toolbar.addWidget(QLabel("Size:"))
        toolbar.addWidget(self._size_slider)
        toolbar.addWidget(self._save_button)
        toolbar.addWidget(self._path_label, stretch=1)

        plate_row = QHBoxLayout()
        plate_row.addWidget(QLabel("Plate:"))
        plate_row.addWidget(self._plate_input, stretch=1)
        plate_row.addWidget(QLabel("Aspect ratio W:H"))
        plate_row.addWidget(self._ratio_width_input)
        plate_row.addWidget(QLabel(":"))
        plate_row.addWidget(self._ratio_height_input)

        pan_row = QHBoxLayout()
        pan_row.addWidget(QLabel("Move all horizontally:"))
        pan_row.addWidget(self._pan_horizontal_slider, stretch=1)
        pan_row.addWidget(QLabel("Move all vertically:"))
        pan_row.addWidget(self._pan_vertical_slider, stretch=1)

        folder_row = QHBoxLayout()
        folder_row.addWidget(self._folder_button)
        folder_row.addWidget(self._folder_label, stretch=1)

        status_row = QHBoxLayout()
        status_row.addWidget(self._status_label, stretch=1)

        layout = QVBoxLayout()
        layout.addLayout(toolbar)
        layout.addLayout(plate_row)
        layout.addLayout(pan_row)
        layout.addLayout(folder_row)
        layout.addLayout(status_row)
        layout.addWidget(self._image_view, stretch=1)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    @property
    def current_image(self) -> LoadedImage | None:
        """The loaded image with its original pixel data, if any."""
        return self._current_image

    @property
    def rectangles(self) -> list[CharacterRect]:
        """Character rectangles in original-image pixel coordinates."""
        return self._rectangles

    @property
    def plate_text(self) -> str:
        """Raw plate field text; not stripped, since blank positions matter."""
        return self._plate_input.text()

    @property
    def destination_folder(self) -> Path | None:
        """The selected destination folder, if any."""
        return self._destination_folder

    def _create_ratio_input(self, placeholder: str) -> QLineEdit:
        """Create one aspect-ratio field (positive number, '.' or ',' decimals)."""
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setFixedWidth(60)
        pattern = QRegularExpression(r"[0-9]*[.,]?[0-9]*")
        field.setValidator(QRegularExpressionValidator(pattern, field))
        field.setToolTip(
            "Locks the rectangle aspect ratio while resizing. "
            "Fill both W and H; leave either empty for free resizing."
        )
        return field

    @staticmethod
    def _create_pan_slider(tooltip: str) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(-1000, 1000)
        slider.setValue(0)
        slider.setSingleStep(1)
        slider.setPageStep(10)
        slider.setToolTip(tooltip)
        return slider

    def _on_open_image(self) -> None:
        path = dialogs.ask_image_path(self, self._last_directory)
        if path is None:
            return  # User cancelled.

        self._load_and_show_image(path)

    def _load_and_show_image(self, path: Path) -> None:
        """Load an image and refresh the current-folder navigation state."""

        try:
            loaded = load_image(path)
        except ImageLoadError as exc:
            # Keep the previously loaded image untouched.
            dialogs.show_error(self, "Cannot open image", str(exc))
            return

        self._current_image = loaded
        self._last_directory = path.parent
        self._image_paths = self._images_in_folder(path.parent)
        if path not in self._image_paths:
            self._image_paths.append(path)
            self._image_paths.sort(key=self._image_sort_key)
        self._image_index = self._image_paths.index(path)
        self._update_image_navigation()
        # Rectangles are hidden and reset every time a new image is opened.
        self._rectangles = []
        self._rectangles_visible = False
        self._size_anchor_rectangles = []
        self._size_anchor_value = self._size_slider.value()
        self._reset_pan_sliders()
        self._place_button.setText("Place rectangles")
        self._image_view.set_image(loaded.pixels)  # Drops any rectangle overlays.
        self._path_label.setText(f"{path}  ({loaded.width} × {loaded.height} px)")
        self._status_label.setText("")

    @staticmethod
    def _image_sort_key(path: Path) -> tuple[tuple[int, str | int], ...]:
        """Return an ascending natural key (A0 before A1, image2 before image10)."""
        parts = re.split(r"(\d+)", path.name.casefold())
        return tuple(
            (1, int(part)) if part.isdigit() else (0, part) for part in parts
        )

    @classmethod
    def _images_in_folder(cls, folder: Path) -> list[Path]:
        supported = {".png", ".jpg", ".jpeg", ".webp"}
        try:
            images = [
                path
                for path in folder.iterdir()
                if path.is_file() and path.suffix.casefold() in supported
            ]
        except OSError:
            return []
        return sorted(images, key=cls._image_sort_key, reverse=False)

    def _navigate_image(self, offset: int) -> None:
        if self._image_index is None:
            return
        target_index = self._image_index + offset
        if 0 <= target_index < len(self._image_paths):
            self._load_and_show_image(self._image_paths[target_index])

    def _update_image_navigation(self) -> None:
        index = self._image_index
        self._previous_image_button.setEnabled(index is not None and index > 0)
        self._next_image_button.setEnabled(
            index is not None and index < len(self._image_paths) - 1
        )

    def _on_place_rectangles(self) -> None:
        """Place the seven rectangles inside the currently visible area.

        The rectangles form a row of touching rectangles, sized by the size
        slider and shaped by the W:H fields when both are filled. The zoom
        level is left untouched, so zooming into the part of interest and
        then clicking the button yields seven complete rectangles fitted into
        that zoomed view, ready to be rearranged. Clicking the button again
        re-places them in the current view.
        """
        image = self._current_image
        if image is None:
            dialogs.show_error(
                self, "Cannot place rectangles", "Open an image first."
            )
            return

        region = self._image_view.visible_image_rect()
        if region is None:
            # Nothing of the image is on screen (should not normally happen);
            # fall back to the whole image.
            region = (0.0, 0.0, float(image.width), float(image.height))
        x, y, width, height = region
        self._rectangles = create_rectangles_in_region(
            x,
            y,
            width,
            height,
            aspect_ratio=self._current_aspect_ratio(),
            size_fraction=self._size_slider.value() / 100,
        )
        self._reset_pan_sliders()
        self._image_view.set_rectangles(self._rectangles)
        self._rectangles_visible = True
        self._capture_size_anchor()
        self._place_button.setText("Re-place rectangles")

    def _on_size_changed(self) -> None:
        """Scale the group around rectangle 1's upper-left corner."""
        if not self._rectangles_visible or not self._size_anchor_rectangles:
            return

        image = self._current_image
        if image is None or self._size_anchor_value <= 0:
            return

        requested_scale = self._size_slider.value() / self._size_anchor_value
        anchor = next(
            (rect for rect in self._size_anchor_rectangles if rect.index == 1),
            self._size_anchor_rectangles[0],
        )
        max_scale = float("inf")
        min_scale = 0.0
        for rect in self._size_anchor_rectangles:
            min_scale = max(min_scale, 2 / rect.width, 2 / rect.height)
            for coordinate, fixed, bound in (
                (rect.x, anchor.x, image.width),
                (rect.x + rect.width, anchor.x, image.width),
                (rect.y, anchor.y, image.height),
                (rect.y + rect.height, anchor.y, image.height),
            ):
                offset = coordinate - fixed
                if offset < 0:
                    max_scale = min(max_scale, fixed / -offset)
                elif offset > 0:
                    max_scale = min(max_scale, (bound - fixed) / offset)

        scale = (
            min(max(requested_scale, min_scale), max_scale)
            if min_scale <= max_scale
            else max_scale
        )
        for index, rect in enumerate(self._size_anchor_rectangles):
            self._rectangles[index].x = anchor.x + (rect.x - anchor.x) * scale
            self._rectangles[index].y = anchor.y + (rect.y - anchor.y) * scale
            self._rectangles[index].width = rect.width * scale
            self._rectangles[index].height = rect.height * scale

        effective_value = round(self._size_anchor_value * scale)
        if effective_value != self._size_slider.value():
            self._size_slider.blockSignals(True)
            self._size_slider.setValue(effective_value)
            self._size_slider.blockSignals(False)
        self._image_view.set_rectangles(self._rectangles)
        self._capture_size_anchor()

    def _capture_size_anchor(self) -> None:
        """Save current geometry as the basis for the next size adjustment."""
        self._size_anchor_rectangles = [
            CharacterRect(rect.index, rect.x, rect.y, rect.width, rect.height)
            for rect in self._rectangles
        ]
        self._size_anchor_value = self._size_slider.value()

    def _reset_pan_sliders(self) -> None:
        self._pan_horizontal_slider.blockSignals(True)
        self._pan_vertical_slider.blockSignals(True)
        self._pan_horizontal_slider.setValue(0)
        self._pan_vertical_slider.setValue(0)
        self._pan_horizontal_slider.blockSignals(False)
        self._pan_vertical_slider.blockSignals(False)
        self._pan_last_values = {"x": 0, "y": 0}

    def _on_group_pan_changed(self, axis: str, value: int) -> None:
        """Translate every rectangle together, keeping the group in the image."""
        if not self._rectangles or self._current_image is None:
            self._pan_last_values[axis] = value
            return

        image = self._current_image
        dimension = image.width if axis == "x" else image.height
        step = dimension * self._pan_range_fraction / 1000
        delta = (value - self._pan_last_values[axis]) * step
        low = min(rect.x if axis == "x" else rect.y for rect in self._rectangles)
        high = max(
            (rect.x + rect.width) if axis == "x" else (rect.y + rect.height)
            for rect in self._rectangles
        )
        limit = dimension
        delta = min(max(delta, -low), limit - high)
        for rect in self._rectangles:
            if axis == "x":
                rect.x += delta
            else:
                rect.y += delta
        actual_steps = round(delta / step) if step else 0
        effective_value = self._pan_last_values[axis] + actual_steps
        slider = self._pan_horizontal_slider if axis == "x" else self._pan_vertical_slider
        if effective_value != value:
            slider.blockSignals(True)
            slider.setValue(effective_value)
            slider.blockSignals(False)
        self._pan_last_values[axis] = effective_value
        self._image_view.set_rectangles(self._rectangles)
        self._capture_size_anchor()

    def _on_select_folder(self) -> None:
        folder = dialogs.ask_directory(self, self._destination_folder)
        if folder is None:
            return  # User cancelled; keep the current selection.

        self._destination_folder = folder
        self._folder_label.setText(str(folder))
        self._folder_label.setToolTip(str(folder))

    def _current_aspect_ratio(self) -> float | None:
        """The locked width / height from the W:H fields, or None if free."""
        return parse_aspect_ratio(
            self._ratio_width_input.text(), self._ratio_height_input.text()
        )

    def _on_aspect_ratio_changed(self) -> None:
        """Apply the W:H fields to the rectangles' resize behaviour."""
        self._image_view.set_aspect_ratio(self._current_aspect_ratio())

    def _on_rectangle_changed(
        self, index: int, x: float, y: float, width: float, height: float
    ) -> None:
        """Keep the stored rectangle in sync with its overlay."""
        for rect in self._rectangles:
            if rect.index == index:
                rect.x, rect.y, rect.width, rect.height = x, y, width, height
                self._capture_size_anchor()
                break

    def _on_save(self) -> None:
        """Validate everything, then save the non-empty character crops."""
        if self._current_image is None:
            dialogs.show_error(self, "Cannot save", "Open an image first.")
            return

        try:
            planned = prepare_save(
                self._current_image,
                self.plate_text,
                self._rectangles,
                self._destination_folder,
            )
        except SaveError as exc:
            dialogs.show_error(self, "Cannot save", str(exc))
            return
        except CropError as exc:
            dialogs.show_error(self, "Invalid crop region", str(exc))
            return

        existing = [crop for crop in planned if crop.exists]
        overwrite = False
        if existing:
            names = [crop.destination.name for crop in existing]
            answer = dialogs.ask_overwrite(self, names)
            if answer is None:
                return  # User cancelled.
            overwrite = answer

        try:
            saved = save_crops(planned, overwrite)
        except OSError as exc:
            dialogs.show_error(self, "Save failed", f"Could not write the files: {exc}")
            return

        if saved:
            self._status_label.setText(
                f"Saved {len(saved)} crop(s) to {self._destination_folder}"
            )
        else:
            self._status_label.setText("Nothing was saved: all files already exist.")
