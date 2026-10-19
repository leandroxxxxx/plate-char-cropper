"""Main application window."""

from pathlib import Path

from PySide6.QtGui import QFontDatabase
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
    create_default_rectangles,
)
from platechar_annotator.services.crop_service import CropError, crop_character
from platechar_annotator.services.image_service import (
    ImageLoadError,
    LoadedImage,
    load_image,
)
from platechar_annotator.ui import dialogs
from platechar_annotator.ui.crop_preview import CropPreview
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
        self._selected_index: int | None = None

        self._open_button = QPushButton("Open image…")
        self._open_button.clicked.connect(self._on_open_image)

        self._path_label = QLabel("No image loaded.")

        self._plate_input = QLineEdit()
        self._plate_input.setPlaceholderText(
            "Plate characters, e.g. ABC1D23 (use spaces for empty positions)"
        )
        self._plate_input.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )

        self._folder_button = QPushButton("Select destination folder…")
        self._folder_button.clicked.connect(self._on_select_folder)

        self._folder_label = QLabel("No destination folder selected.")

        self._image_view = ImageView()
        self._image_view.rectangle_changed.connect(self._on_rectangle_changed)
        self._image_view.rectangle_selected.connect(self._on_rectangle_selected)

        self._crop_preview = CropPreview()

        toolbar = QHBoxLayout()
        toolbar.addWidget(self._open_button)
        toolbar.addWidget(self._path_label, stretch=1)

        plate_row = QHBoxLayout()
        plate_row.addWidget(QLabel("Plate:"))
        plate_row.addWidget(self._plate_input, stretch=1)

        folder_row = QHBoxLayout()
        folder_row.addWidget(self._folder_button)
        folder_row.addWidget(self._folder_label, stretch=1)

        body = QHBoxLayout()
        body.addWidget(self._image_view, stretch=1)
        body.addWidget(self._crop_preview)

        layout = QVBoxLayout()
        layout.addLayout(toolbar)
        layout.addLayout(plate_row)
        layout.addLayout(folder_row)
        layout.addLayout(body, stretch=1)

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
        self._rectangles = create_default_rectangles(loaded.width, loaded.height)
        self._image_view.set_image(loaded.pixels)
        self._image_view.set_rectangles(self._rectangles)
        self._path_label.setText(f"{path}  ({loaded.width} × {loaded.height} px)")

    def _on_select_folder(self) -> None:
        folder = dialogs.ask_directory(self, self._destination_folder)
        if folder is None:
            return  # User cancelled; keep the current selection.

        self._destination_folder = folder
        self._folder_label.setText(str(folder))
        self._folder_label.setToolTip(str(folder))

    def _on_rectangle_changed(
        self, index: int, x: float, y: float, width: float, height: float
    ) -> None:
        """Keep the stored rectangle in sync with its overlay."""
        for rect in self._rectangles:
            if rect.index == index:
                rect.x, rect.y, rect.width, rect.height = x, y, width, height
                break

        if index == self._selected_index:
            self._refresh_preview()

    def _on_rectangle_selected(self, index: int) -> None:
        """Track the selected rectangle (0 = none) and refresh the preview."""
        self._selected_index = index or None
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        """Preview the selected rectangle's crop from the original image."""
        index = self._selected_index
        image = self._current_image
        rect = next((r for r in self._rectangles if r.index == index), None)
        if image is None or rect is None:
            self._crop_preview.clear_preview()
            return

        try:
            crop = crop_character(image.pixels, rect)
        except CropError as exc:
            self._crop_preview.show_message(str(exc))
            return
        self._crop_preview.show_crop(rect.index, crop)