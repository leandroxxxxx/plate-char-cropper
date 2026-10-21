"""Main application window."""

from pathlib import Path

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QFontDatabase, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from platechar_annotator.models.selection import (
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
        self._rectangles: list[CharacterRect] = []
        self._rectangles_visible = False

        self._image_view = ImageView()
        self._image_view.rectangle_changed.connect(self._on_rectangle_changed)

        self._open_button = QPushButton("Open image…")
        self._open_button.clicked.connect(self._on_open_image)

        self._place_button = QPushButton("Place rectangles")
        self._place_button.setToolTip(
            "Place the seven character rectangles inside the currently visible area"
        )
        self._place_button.clicked.connect(self._on_place_rectangles)

        self._zoom_out_button = QPushButton("Zoom −")
        self._zoom_out_button.clicked.connect(self._image_view.zoom_out)

        self._zoom_in_button = QPushButton("Zoom +")
        self._zoom_in_button.clicked.connect(self._image_view.zoom_in)

        self._fit_button = QPushButton("Fit")
        self._fit_button.clicked.connect(self._image_view.fit_to_view)

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
        self._ratio_width_input.textChanged.connect(self._on_aspect_ratio_changed)
        self._ratio_height_input.textChanged.connect(self._on_aspect_ratio_changed)

        self._folder_button = QPushButton("Select destination folder…")
        self._folder_button.clicked.connect(self._on_select_folder)

        self._folder_label = QLabel("No destination folder selected.")

        toolbar = QHBoxLayout()
        toolbar.addWidget(self._open_button)
        toolbar.addWidget(self._place_button)
        toolbar.addWidget(self._zoom_out_button)
        toolbar.addWidget(self._zoom_in_button)
        toolbar.addWidget(self._fit_button)
        toolbar.addWidget(self._save_button)
        toolbar.addWidget(self._path_label, stretch=1)

        plate_row = QHBoxLayout()
        plate_row.addWidget(QLabel("Plate:"))
        plate_row.addWidget(self._plate_input, stretch=1)
        plate_row.addWidget(QLabel("Aspect ratio W:H"))
        plate_row.addWidget(self._ratio_width_input)
        plate_row.addWidget(QLabel(":"))
        plate_row.addWidget(self._ratio_height_input)

        folder_row = QHBoxLayout()
        folder_row.addWidget(self._folder_button)
        folder_row.addWidget(self._folder_label, stretch=1)

        status_row = QHBoxLayout()
        status_row.addWidget(self._status_label, stretch=1)

        layout = QVBoxLayout()
        layout.addLayout(toolbar)
        layout.addLayout(plate_row)
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

    def _on_open_image(self) -> None:
        path = dialogs.ask_image_path(self, self._last_directory)
        if path is None:
            return  # User cancelled.

        try:
            loaded = load_image(path)
        except ImageLoadError as exc:
            # Keep the previously loaded image untouched.
            dialogs.show_error(self, "Cannot open image", str(exc))
            return

        self._current_image = loaded
        self._last_directory = path.parent
        # Rectangles are hidden and reset every time a new image is opened.
        self._rectangles = []
        self._rectangles_visible = False
        self._place_button.setText("Place rectangles")
        self._image_view.set_image(loaded.pixels)  # Drops any rectangle overlays.
        self._path_label.setText(f"{path}  ({loaded.width} × {loaded.height} px)")
        self._status_label.setText("")

    def _on_place_rectangles(self) -> None:
        """Place the seven rectangles inside the currently visible area.

        The zoom level is left untouched, so zooming into the part of
        interest and then clicking the button yields seven complete
        rectangles fitted into that zoomed view, ready to be rearranged.
        Clicking the button again re-places them in the current view.
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
        self._rectangles = create_rectangles_in_region(x, y, width, height)
        self._image_view.set_rectangles(self._rectangles)
        self._rectangles_visible = True
        self._place_button.setText("Re-place rectangles")

    def _on_select_folder(self) -> None:
        folder = dialogs.ask_directory(self, self._destination_folder)
        if folder is None:
            return  # User cancelled; keep the current selection.

        self._destination_folder = folder
        self._folder_label.setText(str(folder))
        self._folder_label.setToolTip(str(folder))

    def _on_aspect_ratio_changed(self) -> None:
        """Apply the W:H fields to the rectangles' resize behaviour."""
        ratio = parse_aspect_ratio(
            self._ratio_width_input.text(), self._ratio_height_input.text()
        )
        self._image_view.set_aspect_ratio(ratio)

    def _on_rectangle_changed(
        self, index: int, x: float, y: float, width: float, height: float
    ) -> None:
        """Keep the stored rectangle in sync with its overlay."""
        for rect in self._rectangles:
            if rect.index == index:
                rect.x, rect.y, rect.width, rect.height = x, y, width, height
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